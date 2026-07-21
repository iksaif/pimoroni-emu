"""Badgeware mock for Pimoroni's badgeware firmware family.

Tufty 2350, Badger 2350, and Blinky 2350 all ship with badgeware:
`screen` is a PicoVector-style `image` (pen/font as properties),
`display` is the underlying display device, `badge` is the input/
system module. The API surface is identical across devices — only
the display dimensions and (TODO) renderer differ. We adapt onto
the existing PicoGraphics mock under the hood, which already
renders to pygame and serializes frames for autosave.

Module name still says `_tufty` for historical reasons; the install
function reads `state["device"]` for dimensions so it works for the
whole family. See badgewa.re/docs for the canonical API reference.
"""

import builtins
import math
import time as _time
from typing import Optional

from emulator import get_state
from emulator.mocks import badgeware as _legacy  # reuse vec2/rect/color/clamp/State
from emulator.mocks.picographics import DISPLAY_TUFTY_2350, PicoGraphics

# ── Re-exports from the legacy (Blinky) badgeware module ─────────────
vec2 = _legacy.vec2
rect = _legacy.rect
color = _legacy.color  # _Color() with rgb(r,g,b[,a]) + named presets
brush = _legacy.brush  # solid/pattern/gradient brushes
clamp = _legacy.clamp
rnd = _legacy.rnd
frnd = _legacy.frnd
State = _legacy.State
scroll_text = _legacy.scroll_text


def set_brightness(value):
    """Set display brightness (LED matrix / e-paper backlight)."""
    if get_state().get("trace"):
        print(f"[badgeware] set_brightness({value})")


def mode(m, force=False):
    """Set the display mode (LORES/HIRES/VSYNC/etc). Forwards to badge.mode."""
    return badge.mode(m)


class AnimatedSprite:
    """Animated sprite — a sequence of frames from a SpriteSheet.

    .frame(i) returns the image at that index, wrapping modulo count.
    """

    def __init__(self, spritesheet, x, y, count, horizontal=True):
        self._sheet = spritesheet
        self._x = x
        self._y = y
        self._horizontal = horizontal
        # Resolve None count to "to edge of sheet"
        if count is None:
            count = (spritesheet.columns - x) if horizontal else (spritesheet.rows - y)
        self.count = count

    def frame(self, frame_index=0):
        if self.count <= 0:
            return self._sheet.sprite(self._x, self._y)
        i = frame_index % self.count
        if self._horizontal:
            return self._sheet.sprite(self._x + i, self._y)
        return self._sheet.sprite(self._x, self._y + i)


class SpriteSheet:
    """Badgeware SpriteSheet — slices a source PNG into a grid of tiles.

    `sheet.sprite(col, row)` returns a cached `image` for that tile.
    `sheet.animation(x, y, count, horizontal)` returns an
    `AnimatedSprite` over a sequence of tiles.
    """

    def __init__(self, source_path, columns, rows):
        self._source_path = source_path
        self.columns = int(columns)
        self.rows = int(rows)
        self._source = image.load(source_path)
        self.tile_w = self._source.width // max(1, self.columns)
        self.tile_h = self._source.height // max(1, self.rows)
        self._cache = {}

    def sprite(self, x, y):
        x, y = int(x), int(y)
        key = (x, y)
        if key in self._cache:
            return self._cache[key]
        tile = image(self.tile_w, self.tile_h)
        # Pre-fill with transparent sentinel so blit alpha works.
        for row in tile._pg._buffer:
            for i in range(len(row)):
                row[i] = image._TRANSPARENT
        # Copy the tile region from the source.
        src_buf = self._source._pg._buffer
        sx0 = x * self.tile_w
        sy0 = y * self.tile_h
        for ty in range(self.tile_h):
            sy = sy0 + ty
            if 0 <= sy < self._source.height:
                src_row = src_buf[sy]
                dst_row = tile._pg._buffer[ty]
                for tx in range(self.tile_w):
                    sx = sx0 + tx
                    if 0 <= sx < self._source.width:
                        dst_row[tx] = src_row[sx]
        self._cache[key] = tile
        return tile

    def animation(self, x=0, y=0, count=None, horizontal=True):
        return AnimatedSprite(self, x, y, count, horizontal)
HIRES = _legacy.HIRES
LORES = _legacy.LORES
VSYNC = 2
FAST_UPDATE = 3 << 4
FULL_UPDATE = 0 << 4
MEDIUM_UPDATE = 2 << 4
NON_BLOCKING = 1 << 9
DITHER = 1 << 8

# Tufty buttons — distinct sentinels (real hw uses machine.Pin objects)
BUTTON_A = "BUTTON_A"
BUTTON_B = "BUTTON_B"
BUTTON_C = "BUTTON_C"
BUTTON_UP = "BUTTON_UP"
BUTTON_DOWN = "BUTTON_DOWN"
BUTTON_HOME = "BUTTON_HOME"

_PIN_TO_BUTTON = {
    # Tufty 2350 button pins
    7: BUTTON_A, 8: BUTTON_B, 9: BUTTON_C, 22: BUTTON_UP, 6: BUTTON_DOWN,
    # Badger 2350 button pins
    12: BUTTON_A, 13: BUTTON_B, 14: BUTTON_C, 15: BUTTON_UP, 11: BUTTON_DOWN,
}


# ── mat3 ─────────────────────────────────────────────────────────────
class mat3:
    """Affine transform — translate/scale/rotate, chainable."""

    def __init__(self, tx=0.0, ty=0.0, sx=1.0, sy=1.0, rot=0.0):
        self._tx, self._ty = float(tx), float(ty)
        self._sx, self._sy = float(sx), float(sy)
        self._rot = float(rot)

    def translate(self, dx, dy):
        return mat3(self._tx + float(dx), self._ty + float(dy), self._sx, self._sy, self._rot)

    def scale(self, sx, sy=None):
        if sy is None:
            sy = sx
        return mat3(self._tx, self._ty, self._sx * float(sx), self._sy * float(sy), self._rot)

    def rotate(self, radians):
        return mat3(self._tx, self._ty, self._sx, self._sy, self._rot + float(radians))

    def apply(self, x, y):
        x = float(x) * self._sx
        y = float(y) * self._sy
        if self._rot:
            c, s = math.cos(self._rot), math.sin(self._rot)
            x, y = x * c - y * s, x * s + y * c
        return x + self._tx, y + self._ty


# ── Fonts ────────────────────────────────────────────────────────────
# The upstream firmware renders Pimoroni `.ppf` pixel fonts at their true
# on-device sizes (e.g. sins=12px, nope=13px, smart=16px, ignore=28px).
# We parse and rasterise those files directly so text in the emulator is
# the right size and width — rather than collapsing every font onto a
# couple of fixed-size PicoGraphics bitmap fonts.

import struct as _struct

from emulator.mocks.fonts import _UNICODE_TO_ASCII

# Cache of parsed .ppf fonts keyed by resolved host path (None = miss).
_PPF_CACHE: dict = {}


class _PPFFont:
    """A parsed Pimoroni pixel font (.ppf).

    Binary layout (big-endian), per vendor pixel_font.cpp:
        'ppf!' | u16 flags | u32 glyph_count | u16 width | u16 height |
        char[32] name | glyph_count×(u32 codepoint, u16 width) |
        glyph_count × (1bpp bitmap, MSB-first, bytes_per_row from the
        font's max `width`, `height` rows).
    Advance is `glyph.width + 1`; a space advances by `width // 3`.
    """

    def __init__(self, width, height, index, widths, data, gds, bpr):
        self.width = width        # font max glyph width (sets bytes/row)
        self.height = height
        self._index = index       # codepoint -> glyph slot
        self._widths = widths     # per-slot advance width
        self._data = data         # concatenated glyph bitmaps
        self._gds = gds           # bytes per glyph
        self._bpr = bpr           # bytes per row

    @staticmethod
    def try_load(local_path):
        try:
            with open(local_path, "rb") as f:
                blob = f.read()
        except OSError:
            return None
        if len(blob) < 46 or blob[:4] != b"ppf!":
            return None
        (count,) = _struct.unpack_from(">I", blob, 6)
        (gw,) = _struct.unpack_from(">H", blob, 10)
        (gh,) = _struct.unpack_from(">H", blob, 12)
        bpr = (gw + 7) >> 3
        gds = bpr * gh
        index = {}
        widths = [0] * count
        off = 46
        try:
            for i in range(count):
                cp, = _struct.unpack_from(">I", blob, off)
                w, = _struct.unpack_from(">H", blob, off + 4)
                index[cp] = i
                widths[i] = w
                off += 6
        except _struct.error:
            return None
        data = blob[off:off + gds * count]
        if len(data) < gds * count:
            return None
        return _PPFFont(gw, gh, index, widths, data, gds, bpr)

    def _slot(self, cp):
        gi = self._index.get(cp)
        if gi is None:
            sub = _UNICODE_TO_ASCII.get(cp)
            if sub:
                gi = self._index.get(ord(sub))
        return gi

    def measure(self, text):
        space = max(1, self.width // 3)
        w = 0
        for ch in text:
            cp = ord(ch)
            if cp == 32:
                w += space
                continue
            gi = self._slot(cp)
            if gi is not None:
                w += self._widths[gi] + 1
        return (w, self.height)

    def render(self, set_pixel, x, y, text):
        """Stamp glyphs via `set_pixel(px, py)` (e.g. PicoGraphics.pixel,
        so the current pen and clip rect apply automatically)."""
        bpr = self._bpr
        h = self.height
        gds = self._gds
        data = self._data
        space = max(1, self.width // 3)
        cx = x
        for ch in text:
            cp = ord(ch)
            if cp == 32:
                cx += space
                continue
            gi = self._slot(cp)
            if gi is None:
                cx += space
                continue
            gw = self._widths[gi]
            base = gds * gi
            for row in range(h):
                ro = base + row * bpr
                py = y + row
                for bit in range(gw):
                    if data[ro + (bit >> 3)] & (0x80 >> (bit & 0x7)):
                        set_pixel(cx + bit, py)
            cx += gw + 1
        return cx - x


class _PixelFont:
    """Handle for a pixel font. Resolves a `.ppf` by name
    (`rom_font.<name>` → /rom/fonts/<name>.ppf) or explicit path, parses
    it lazily, and caches the result. Falls back to a PicoGraphics bitmap
    font only when the `.ppf` can't be found."""

    def __init__(self, name="sins", path=None):
        self.name = name
        self._path = path
        self._resolved = False
        self._ppf = None

    def _ppf_font(self):
        if self._resolved:
            return self._ppf
        self._resolved = True
        from emulator.mocks import _translate_path
        raw = self._path if self._path else f"/rom/fonts/{self.name}.ppf"
        local = _translate_path(raw)
        if local in _PPF_CACHE:
            self._ppf = _PPF_CACHE[local]
        else:
            self._ppf = _PPFFont.try_load(local)
            _PPF_CACHE[local] = self._ppf
        return self._ppf

    @property
    def height(self):
        ppf = self._ppf_font()
        return ppf.height if ppf else 8

    def _pg_name(self):
        # Fallback PG bitmap font, used only if the real .ppf is missing.
        ppf = self._ppf_font()
        return "bitmap6" if (ppf and ppf.height <= 6) else "bitmap8"


class _PixelFontLoader:
    """Callable `pixel_font` — supports `pixel_font.load(path)`."""

    def load(self, path):
        # Derive a font name from the filename stem (e.g. /rom/fonts/sins.ppf → sins)
        name = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return _PixelFont(name, path=path)


pixel_font = _PixelFontLoader()


def load_font(path):
    """Load a pixel font from a path (badgeware `load_font` builtin)."""
    return pixel_font.load(path)


class _ROMFonts:
    """`rom_font.<name>` returns a _PixelFont, and `dir(rom_font)` lists
    every font that ships in the vendor romfs/fonts/ directory so apps
    can do `font_list = dir(rom_font)` and pick by name.
    """

    def __getattr__(self, key):
        return _PixelFont(key)

    def __dir__(self):
        # Enumerate from the active device's romfs (vendor/<board>/romfs/fonts/).
        import os

        from emulator.mocks import _translate_path
        try:
            local = _translate_path("/rom/fonts")
            return sorted(
                f[:-4] for f in os.listdir(local) if f.endswith(".ppf")
            )
        except (OSError, FileNotFoundError):
            return ["sins", "ark"]


rom_font = _ROMFonts()


# ── Shapes ───────────────────────────────────────────────────────────
class _Shape:
    """A geometric primitive. `screen.shape(s)` rasterizes it through
    the PicoGraphics mock. Holds an optional transform (mat3) and
    stroke width (>0 = outline, 0 = filled)."""

    def __init__(self, kind, args, transform=None, stroke_width=0):
        self.kind = kind
        self.args = tuple(args)
        self._transform = transform
        self._stroke = stroke_width

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, value):
        self._transform = value

    def stroke(self, width):
        return _Shape(self.kind, self.args, transform=self._transform, stroke_width=int(width))


class _ShapeFactory:
    """`shape` — factory for creating shape primitives."""

    @staticmethod
    def circle(x, y, r):
        return _Shape("circle", (x, y, r))

    @staticmethod
    def rectangle(*args):
        # rectangle(rect_obj), rectangle(x, y, w, h),
        # or rectangle(x, y, w, h, corner_radius) — last alias for
        # rounded_rectangle with uniform radius.
        if len(args) == 1:
            r = args[0]
            return _Shape("rectangle", (r.x, r.y, r.w, r.h))
        if len(args) == 5:
            x, y, w, h, r = args
            return _Shape("rounded_rectangle", (x, y, w, h, r, r, r, r))
        return _Shape("rectangle", args)

    @staticmethod
    def rounded_rectangle(x, y, w, h, r1=0, r2=None, r3=None, r4=None):
        # Upstream signature: x, y, w, h, r1, r2, r3, r4 (per-corner radii)
        if r2 is None:
            r2 = r1
        if r3 is None:
            r3 = r1
        if r4 is None:
            r4 = r1
        return _Shape("rounded_rectangle", (x, y, w, h, r1, r2, r3, r4))

    @staticmethod
    def squircle(x, y, r, radius=4):
        return _Shape("squircle", (x, y, r, radius))

    @staticmethod
    def star(x, y, num_points, inner_r, outer_r):
        return _Shape("star", (x, y, num_points, inner_r, outer_r))

    @staticmethod
    def pie(x, y, r, start_deg, end_deg):
        return _Shape("pie", (x, y, r, start_deg, end_deg))

    @staticmethod
    def arc(x, y, r_inner, r_outer, start_deg, end_deg):
        return _Shape("arc", (x, y, r_inner, r_outer, start_deg, end_deg))

    @staticmethod
    def line(*args):
        # line(p1, p2[, thickness]) or line(x0, y0, x1, y1[, thickness])
        if len(args) == 2 or (len(args) == 3 and hasattr(args[0], "x")):
            a, b = args[0], args[1]
            base = (a.x, a.y, b.x, b.y)
            thickness = args[2] if len(args) == 3 else 1
        else:
            base = args[:4]
            thickness = args[4] if len(args) >= 5 else 1
        return _Shape("line", base + (thickness,))

    @staticmethod
    def regular_polygon(x, y, sides, radius):
        return _Shape("regular_polygon", (x, y, sides, radius))

    @staticmethod
    def custom(points):
        """Arbitrary polygon from a list of vec2 (or (x,y)) points."""
        flat = [(p.x, p.y) if hasattr(p, 'x') else (p[0], p[1]) for p in points]
        return _Shape("custom", (flat,))


shape = _ShapeFactory()


def _shape_points(shape_obj):
    """Compute the polygon vertices for a shape, after applying its
    transform. Returns (points, closed) — closed=True for fillable
    shapes, False for line-strips."""
    k = shape_obj.kind
    args = shape_obj.args
    pts = []
    closed = True

    if k == "circle":
        cx, cy, r = args
        segments = max(12, int(r * 2))
        pts = [(cx + r * math.cos(2 * math.pi * i / segments),
                cy + r * math.sin(2 * math.pi * i / segments))
               for i in range(segments)]

    elif k == "rectangle":
        x, y, w, h = args
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    elif k == "rounded_rectangle":
        x, y, w, h, r1, r2, r3, r4 = args
        # Approximate with corner arcs — clamp radii to half-side.
        max_r = min(w, h) / 2
        r1, r2, r3, r4 = (min(r, max_r) for r in (r1, r2, r3, r4))
        seg = 6
        # Top-left, top-right, bottom-right, bottom-left
        for cx, cy, rad, start_a in (
            (x + r1, y + r1, r1, math.pi),
            (x + w - r2, y + r2, r2, 3 * math.pi / 2),
            (x + w - r3, y + h - r3, r3, 0),
            (x + r4, y + h - r4, r4, math.pi / 2),
        ):
            for i in range(seg + 1):
                a = start_a + (math.pi / 2) * i / seg
                pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))

    elif k == "squircle":
        cx, cy, r, _radius = args
        # Approximate squircle with a 24-vertex superellipse, n=4.
        n = 4
        segments = 24
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ca, sa = math.cos(a), math.sin(a)
            x = math.copysign(abs(ca) ** (2 / n), ca) * r
            y = math.copysign(abs(sa) ** (2 / n), sa) * r
            pts.append((cx + x, cy + y))

    elif k == "star":
        cx, cy, num_points, inner_r, outer_r = args
        for i in range(2 * num_points):
            r = outer_r if i % 2 == 0 else inner_r
            a = math.pi * i / num_points - math.pi / 2
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    elif k == "pie":
        cx, cy, r, sd, ed = args
        sa, ea = math.radians(sd), math.radians(ed)
        if ea < sa:
            ea += 2 * math.pi
        segments = max(8, int((ea - sa) * 12))
        pts = [(cx, cy)]
        for i in range(segments + 1):
            a = sa + (ea - sa) * i / segments
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    elif k == "arc":
        cx, cy, ri, ro, sd, ed = args
        sa, ea = math.radians(sd), math.radians(ed)
        if ea < sa:
            ea += 2 * math.pi
        segments = max(8, int((ea - sa) * 12))
        outer = [(cx + ro * math.cos(sa + (ea - sa) * i / segments),
                  cy + ro * math.sin(sa + (ea - sa) * i / segments))
                 for i in range(segments + 1)]
        inner = [(cx + ri * math.cos(sa + (ea - sa) * i / segments),
                  cy + ri * math.sin(sa + (ea - sa) * i / segments))
                 for i in range(segments, -1, -1)]
        pts = outer + inner

    elif k == "line":
        # args is (x0, y0, x1, y1, thickness); thickness is rendered as
        # a 1px line for now — improvement TODO.
        x0, y0, x1, y1 = args[:4]
        pts = [(x0, y0), (x1, y1)]
        closed = False

    elif k == "regular_polygon":
        cx, cy, sides, r = args
        pts = [(cx + r * math.cos(2 * math.pi * i / sides - math.pi / 2),
                cy + r * math.sin(2 * math.pi * i / sides - math.pi / 2))
               for i in range(sides)]

    elif k == "custom":
        pts = list(args[0])

    # Apply transform
    if shape_obj._transform is not None:
        pts = [shape_obj._transform.apply(px, py) for px, py in pts]

    return pts, closed


# ── Pattern brushes ──────────────────────────────────────────────────
# The 38 embedded 8x8 dither patterns from vendor picovector
# brushes/pattern.cpp. brush.pattern(c1, c2, index) fills each pixel with
# c1 where the pattern bit is set (else c2), tiled on absolute (x, y):
#   bit = patterns[index][y & 7] ; c1 if bit & (1 << (7 - (x & 7))) else c2
# Without this every brush.pattern() pen collapsed to solid white, losing
# the badge/menu greyscale backgrounds.
_PATTERNS = [
    (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    (0x22, 0x00, 0x88, 0x00, 0x22, 0x00, 0x88, 0x00),
    (0x22, 0x88, 0x22, 0x88, 0x22, 0x88, 0x22, 0x88),
    (0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA),
    (0xAA, 0x00, 0xAA, 0x00, 0xAA, 0x00, 0xAA, 0x00),
    (0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55),
    (0x11, 0x22, 0x44, 0x88, 0x11, 0x22, 0x44, 0x88),
    (0x77, 0x77, 0x77, 0x77, 0x77, 0x77, 0x77, 0x77),
    (0x4E, 0xCF, 0xFC, 0xE4, 0x27, 0x3F, 0xF3, 0x72),
    (0x7F, 0xEF, 0xFD, 0xDF, 0xFE, 0xF7, 0xBF, 0xFB),
    (0x00, 0x77, 0x77, 0x77, 0x00, 0x77, 0x77, 0x77),
    (0x00, 0x7F, 0x7F, 0x7F, 0x00, 0xF7, 0xF7, 0xF7),
    (0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
    (0x7F, 0xBF, 0xDF, 0xFF, 0xFD, 0xFB, 0xF7, 0xFF),
    (0x7D, 0xBB, 0xC6, 0xBB, 0x7D, 0xFE, 0xFE, 0xFE),
    (0x07, 0x8B, 0xDD, 0xB8, 0x70, 0xE8, 0xDD, 0x8E),
    (0xAA, 0x5F, 0xBF, 0xBF, 0xAA, 0xF5, 0xFB, 0xFB),
    (0xDF, 0xAF, 0x77, 0x77, 0x77, 0x77, 0xFA, 0xFD),
    (0x40, 0xFF, 0x40, 0x40, 0x4F, 0x4F, 0x4F, 0x4F),
    (0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
    (0x7F, 0xFF, 0xF7, 0xFF, 0x7F, 0xFF, 0xF7, 0xFF),
    (0x77, 0xFF, 0xDD, 0xFF, 0x77, 0xFF, 0xDD, 0xFF),
    (0x77, 0xDD, 0x77, 0xDD, 0x77, 0xDD, 0x77, 0xDD),
    (0x55, 0xFF, 0x55, 0xFF, 0x55, 0xFF, 0x55, 0xFF),
    (0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF),
    (0xEE, 0xDD, 0xBB, 0x77, 0xEE, 0xDD, 0xBB, 0x77),
    (0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0xFF, 0xFF),
    (0xFE, 0xFD, 0xFB, 0xF7, 0xEF, 0xDF, 0xBF, 0x7F),
    (0x55, 0xFF, 0x7F, 0xFF, 0x77, 0xFF, 0x7F, 0xFF),
    (0x00, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F),
    (0xF7, 0xE3, 0xDD, 0x3E, 0x7F, 0xFE, 0xFD, 0xFB),
    (0x77, 0xEB, 0xDD, 0xBE, 0x77, 0xFF, 0x55, 0xFF),
    (0xBF, 0x5F, 0xFF, 0xFF, 0xFB, 0xF5, 0xFF, 0xFF),
    (0xFC, 0x7B, 0xB7, 0xCF, 0xF3, 0xFD, 0xFE, 0xFE),
    (0x7F, 0x7F, 0xBE, 0xC1, 0xF7, 0xF7, 0xEB, 0x1C),
    (0xEF, 0xDF, 0xAB, 0x55, 0x00, 0xFD, 0xFB, 0xF7),
    (0x88, 0x76, 0x70, 0x70, 0x88, 0x67, 0x07, 0x07),
    (0xFF, 0xF7, 0xEB, 0xD5, 0xAA, 0xD5, 0xEB, 0xF7),
]


def _color_to_rgb24(c):
    """Convert a badgeware RGBA-packed color int → PicoGraphics 24-bit RGB."""
    if not isinstance(c, int):
        return 0xFFFFFF
    return (((c >> 24) & 0xFF) << 16) | (((c >> 16) & 0xFF) << 8) | ((c >> 8) & 0xFF)


# ── image ────────────────────────────────────────────────────────────
# Antialias constants (held on the class — apps reference image.X4)
class image:
    """Color-aware image. The primary instance is `screen`, backed by
    a PicoGraphics(DISPLAY_TUFTY_2350) — drawing flows through there."""

    OFF = 0
    X2 = 1
    X4 = 2

    def __init__(self, width, height, _pg=None, is_screen=False):
        # Native (panel) dimensions — what the backing PicoGraphics is
        # actually allocated at. `width`/`height` below report the
        # mode-dependent logical dimensions for `screen`, so apps see
        # 160x120 in LORES and 320x240 in HIRES (matching real Tufty
        # firmware where `display.fullres(False)` halves screen.WIDTH).
        self._native_w = int(width)
        self._native_h = int(height)
        self._is_screen = bool(is_screen)
        # Use a real PicoGraphics for `screen` (so update() pushes to
        # the emulator display). Off-screen images get their own.
        self._pg = _pg if _pg is not None else PicoGraphics(
            display=DISPLAY_TUFTY_2350, width=self._native_w, height=self._native_h
        )
        self._pen = color.rgb(255, 255, 255)
        self._font = _PixelFont("sins")
        self.antialias = image.OFF
        self.alpha = 255
        self.clip = rect(0, 0, self._native_w, self._native_h)
        # Apply default pen + font on the PG side
        self._sync_pen()
        self._sync_font()

    @property
    def width(self):
        # E-ink devices ignore LORES — FAST_UPDATE/NON_BLOCKING don't halve resolution.
        if self._is_screen and (badge._mode & HIRES) == 0 and not getattr(self, '_force_hires', False):
            return self._native_w // 2
        return self._native_w

    @property
    def height(self):
        if self._is_screen and (badge._mode & HIRES) == 0 and not getattr(self, '_force_hires', False):
            return self._native_h // 2
        return self._native_h

    # Sentinel for "transparent" pixel in our RGB buffer. PicoGraphics
    # uses a 24-bit RGB int per pixel, so we steal an unused bit pattern
    # (negative) to mark untouched/alpha=0 pixels for blit().
    _TRANSPARENT = -1

    @staticmethod
    def load(path):
        """Load a PNG and return an off-screen `image`. Resolves
        upstream /system/... paths via the VFS translation layer."""
        from emulator.mocks import _translate_path
        try:
            from PIL import Image as _PIL_Image
        except ImportError:
            return image(16, 16)
        local = _translate_path(path)
        try:
            with _PIL_Image.open(local) as src:
                src = src.convert("RGBA")
                img = image(src.width, src.height)
                # Pre-fill with the transparent sentinel; only stamp
                # pixels where alpha > 0.
                for row in img._pg._buffer:
                    for i in range(len(row)):
                        row[i] = image._TRANSPARENT
                for y in range(src.height):
                    for x in range(src.width):
                        r, g, b, a = src.getpixel((x, y))
                        if a > 0:
                            img._pg._buffer[y][x] = (r << 16) | (g << 8) | b
                return img
        except Exception:  # noqa: BLE001
            return image(16, 16)

    # Pen
    @property
    def pen(self):
        return self._pen

    @pen.setter
    def pen(self, value):
        self._pen = value
        self._sync_pen()

    def _sync_pen(self):
        # color values produced by _Color.rgb() are packed (r<<24)|(g<<16)|(b<<8)|a
        p = self._pen
        if isinstance(p, tuple):
            # Brush: solid/gradient/pattern. Set a representative solid
            # colour for any primitive that doesn't special-case the
            # brush (gradient → start, pattern → fg). Pattern fills route
            # through _brush_at() for true per-pixel dithering.
            c = p[1] if (len(p) > 1 and isinstance(p[1], int)) else 0xFFFFFFFF
        elif isinstance(p, int):
            c = p
        else:
            c = 0xFFFFFFFF
        r = (c >> 24) & 0xFF
        g = (c >> 16) & 0xFF
        b = (c >> 8) & 0xFF
        self._pg.set_pen(self._pg.create_pen(r, g, b))

    def _brush_at(self):
        """If the current pen is a pattern brush, return a fn(x, y) →
        packed RGB24 that selects the dither colour per pixel. Otherwise
        None — callers use the fast solid PicoGraphics pen."""
        p = self._pen
        if isinstance(p, tuple) and p and p[0] == "pattern" and len(p) == 4:
            _, fg, bg, idx = p
            pat = _PATTERNS[int(idx) % len(_PATTERNS)]
            fg24 = _color_to_rgb24(fg)
            bg24 = _color_to_rgb24(bg)

            def fn(x, y, pat=pat, fg24=fg24, bg24=bg24):
                return fg24 if (pat[y & 7] & (0x80 >> (x & 7))) else bg24

            return fn
        return None

    # Font
    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value
        self._sync_font()

    def _sync_font(self):
        f = self._font
        if isinstance(f, _PixelFont):
            self._pg.set_font(f._pg_name())

    # Drawing primitives
    def clear(self):
        """Fill with current pen, honoring its alpha channel.

        At alpha=255 (fully opaque) this is a fast overwrite; below
        255 we alpha-blend over the existing framebuffer so effects
        like the launcher menu's fade-in render correctly. alpha=0
        is a no-op. A pattern brush fills with its dithered colours.
        """
        fn = self._brush_at()
        if fn is not None:
            buf = self._pg._buffer
            for y in range(self._native_h):
                row = buf[y]
                for x in range(self._native_w):
                    row[x] = fn(x, y)
            return
        a = self._pen & 0xFF if isinstance(self._pen, int) else 255
        if a >= 255:
            self._pg.clear()
            return
        if a == 0:
            return
        r = (self._pen >> 24) & 0xFF
        g = (self._pen >> 16) & 0xFF
        b = (self._pen >> 8) & 0xFF
        af = a / 255.0
        inv = 1.0 - af
        buf = self._pg._buffer
        for y in range(self.height):
            row = buf[y]
            for x in range(self.width):
                old = row[x]
                if old < 0:  # transparent sentinel — leave alone
                    continue
                dr = (old >> 16) & 0xFF
                dg = (old >> 8) & 0xFF
                db = old & 0xFF
                nr = int(r * af + dr * inv)
                ng = int(g * af + dg * inv)
                nb = int(b * af + db * inv)
                row[x] = (nr << 16) | (ng << 8) | nb

    def put(self, x, y):
        self._pg.pixel(int(x), int(y))

    def pixel(self, x, y):
        self._pg.pixel(int(x), int(y))

    def get(self, x, y):
        # Return packed color tuple; close enough for the few callers
        try:
            v = self._pg._buffer[int(y)][int(x)]
        except (IndexError, AttributeError):
            return color.rgb(0, 0, 0)
        r = (v >> 16) & 0xFF
        g = (v >> 8) & 0xFF
        b = v & 0xFF
        return color.rgb(r, g, b)

    def rectangle(self, *args):
        if len(args) == 1:
            r = args[0]
            x, y, w, h = r.x, r.y, r.w, r.h
        else:
            x, y, w, h = args
        x, y, w, h = int(x), int(y), int(w), int(h)
        fn = self._brush_at()
        if fn is not None:
            buf = self._pg._buffer
            for yy in range(max(0, y), min(self._native_h, y + h)):
                row = buf[yy]
                for xx in range(max(0, x), min(self._native_w, x + w)):
                    row[xx] = fn(xx, yy)
            return
        self._pg.rectangle(x, y, w, h)

    def circle(self, *args):
        if len(args) == 2:
            p, r = args
            x, y = p.x, p.y
        else:
            x, y, r = args
        self._pg.circle(int(x), int(y), int(r))

    def triangle(self, *args):
        if len(args) == 3:
            pts = [(a.x, a.y) for a in args]
        else:
            pts = [(args[0], args[1]), (args[2], args[3]), (args[4], args[5])]
        self._fill_polygon(pts)

    def line(self, *args):
        if len(args) == 2:
            a, b = args
            x0, y0, x1, y1 = a.x, a.y, b.x, b.y
        else:
            x0, y0, x1, y1 = args
        self._pg.line(int(x0), int(y0), int(x1), int(y1))

    def text(self, message, *args):
        # text(s, vec2) or text(s, x, y) — `size` arg is for vector
        # fonts; we just ignore it (pixel fonts only).
        if len(args) == 1:  # vec2
            x, y = args[0].x, args[0].y
        else:
            x, y = args[0], args[1]
        x, y = int(x), int(y)
        f = self._font
        if isinstance(f, _PixelFont):
            ppf = f._ppf_font()
            if ppf:
                brush_fn = self._brush_at()
                if brush_fn is None:
                    # Render through pg.pixel so the current pen + clip
                    # apply, exactly like the other drawing primitives.
                    ppf.render(self._pg.pixel, x, y, str(message))
                else:
                    buf = self._pg._buffer
                    W, H = self._native_w, self._native_h

                    def _sp(px, py, buf=buf, W=W, H=H, fn=brush_fn):
                        if 0 <= px < W and 0 <= py < H:
                            buf[py][px] = fn(px, py)

                    ppf.render(_sp, x, y, str(message))
                return
        self._pg.text(str(message), x, y)

    def measure_text(self, message, size=None):
        f = self._font
        if isinstance(f, _PixelFont):
            ppf = f._ppf_font()
            if ppf:
                return ppf.measure(str(message))
        w = self._pg.measure_text(str(message))
        h = f.height if isinstance(f, _PixelFont) else 8
        return (int(w), int(h))

    def shape(self, shape_obj):
        """Rasterize a vector shape onto the framebuffer."""
        pts, closed = _shape_points(shape_obj)
        if not pts:
            return
        if not closed:
            # Line-strip: draw with line primitives
            for i in range(len(pts) - 1):
                self._pg.line(int(pts[i][0]), int(pts[i][1]),
                              int(pts[i + 1][0]), int(pts[i + 1][1]))
            return
        if shape_obj._stroke > 0:
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                self._pg.line(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
            return
        self._fill_polygon(pts)

    def _fill_polygon(self, pts):
        """Scanline-fill a polygon onto the underlying PG buffer."""
        if len(pts) < 3:
            return
        brush_fn = self._brush_at()
        buf = self._pg._buffer
        int_pts = [(p[0], p[1]) for p in pts]
        min_y = max(0, int(min(p[1] for p in int_pts)))
        max_y = min(self.height - 1, int(max(p[1] for p in int_pts)))
        n = len(int_pts)
        for y in range(min_y, max_y + 1):
            xs = []
            for i in range(n):
                x1, y1 = int_pts[i]
                x2, y2 = int_pts[(i + 1) % n]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y < max(y1, y2):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[i]))
                xb = min(self.width - 1, int(xs[i + 1]))
                if brush_fn is not None:
                    row = buf[y]
                    for x in range(xa, xb + 1):
                        row[x] = brush_fn(x, y)
                else:
                    for x in range(xa, xb + 1):
                        self._pg.pixel(x, y)

    def blit(self, src, *args, **kwargs):
        """Blit another image onto this one.

        Supported call forms:
          blit(src, vec2)
          blit(src, x, y)
          blit(src, dst_rect)
          blit(src, src_rect, dst_rect)

        Transparent source pixels (image._TRANSPARENT sentinel from PNG
        alpha=0) are skipped so loaded sprites composite correctly.
        Scaling for the (src_rect, dst_rect) form is approximated via
        nearest-neighbour sampling.
        """
        # Resolve source region and destination position/size
        src_x, src_y, src_w, src_h = 0, 0, src.width, src.height
        dst_x, dst_y, dst_w, dst_h = 0, 0, src.width, src.height

        if len(args) == 2 and isinstance(args[0], rect) and isinstance(args[1], rect):
            sr, dr = args
            src_x, src_y, src_w, src_h = int(sr.x), int(sr.y), int(sr.w), int(sr.h)
            dst_x, dst_y, dst_w, dst_h = int(dr.x), int(dr.y), int(dr.w), int(dr.h)
        elif len(args) == 1:
            a = args[0]
            if isinstance(a, rect):
                dst_x, dst_y, dst_w, dst_h = int(a.x), int(a.y), int(a.w), int(a.h)
            else:
                dst_x, dst_y = int(a.x), int(a.y)
        else:
            dst_x, dst_y = int(args[0]), int(args[1])

        # Nearest-neighbour blit. When dst_w/dst_h match src_w/src_h
        # this collapses to a straight copy.
        if dst_w <= 0 or dst_h <= 0:
            return
        for dy in range(dst_h):
            sy = src_y + (dy * src_h) // dst_h
            if not (0 <= sy < src.height):
                continue
            src_row = src._pg._buffer[sy]
            ty = dst_y + dy
            if not (0 <= ty < self.height):
                continue
            dst_row = self._pg._buffer[ty]
            for dx in range(dst_w):
                sx = src_x + (dx * src_w) // dst_w
                if not (0 <= sx < src.width):
                    continue
                v = src_row[sx]
                if v == image._TRANSPARENT:
                    continue
                tx = dst_x + dx
                if 0 <= tx < self.width:
                    dst_row[tx] = v

    # Filters
    def blur(self, radius):
        pass  # not implemented; apps tolerate this being a no-op

    def dither(self, *args, **kwargs):
        pass

    # Surface-level helpers
    def window(self, x, y, w, h):
        return self  # crude — full upstream returns a sub-surface


# ── display, badge ───────────────────────────────────────────────────
class _Display:
    """Wraps the PicoGraphics behind `screen` so apps can do
    `display.update()` and `display.set_backlight(b)`."""

    def __init__(self):
        self._screen = None
        self._mode = LORES | VSYNC

    def bind(self, screen_image):
        self._screen = screen_image

    @property
    def WIDTH(self):
        return self._screen.width if self._screen else 320

    @property
    def HEIGHT(self):
        return self._screen.height if self._screen else 240

    def update(self):
        if self._screen is None:
            return
        pg = self._screen._pg
        # LORES: apps drew into the upper-left logical_w x logical_h
        # region; real Tufty hardware scales 2x to fill the panel via
        # `display.fullres(False)`. Replicate by nearest-neighbour
        # 2x upscaling that region into the full framebuffer before
        # we push to the emulator's display renderer.
        #
        # E-ink panels (Badger) have no half-res mode — they always run
        # native. Honour `_force_hires` exactly like image.width/height
        # do, otherwise an app that sets FAST_UPDATE|NON_BLOCKING (which
        # clears the HIRES bit) would get its top-left quadrant blown up
        # 2x to fill the panel, i.e. doubled and cut off.
        if (self._screen._is_screen and (badge._mode & HIRES) == 0
                and not getattr(self._screen, '_force_hires', False)):
            lw = pg.WIDTH // 2
            lh = pg.HEIGHT // 2
            buf = pg._buffer
            # Snapshot the source region so writes to the panel half
            # don't corrupt unread cells in the upper-left quadrant.
            src = [row[:lw] for row in buf[:lh]]
            for sy in range(lh):
                top = buf[sy * 2]
                bot = buf[sy * 2 + 1]
                row = src[sy]
                for sx in range(lw):
                    v = row[sx]
                    dx = sx * 2
                    top[dx] = v
                    top[dx + 1] = v
                    bot[dx] = v
                    bot[dx + 1] = v
        pg.update()

    def set_backlight(self, value):
        pass

    def backlight(self, value):
        pass

    def fullres(self, on):
        pass

    def set_vsync(self, on):
        pass


display = _Display()


class _Badge:
    """Tufty input + system module.

    Edge state (pressed/released) is computed by diffing `held` between
    successive `poll()` calls. Held state reads from the emulator's
    shared button registry (mocks/machine.py keeps it in get_state()).
    """

    def __init__(self):
        self._ticks_start_ms = _time.time() * 1000
        self._prev_held: set = set()
        self._held: set = set()
        self._pressed: set = set()
        self._released: set = set()
        self.default_clear: Optional[int] = None
        self.default_pen: int = color.rgb(255, 255, 255)
        self._mode = LORES | VSYNC
        # 4 rear lighting zones (CL0..CL3). Values are 0.0..1.0 brightness.
        self._case_light_values = [0.0, 0.0, 0.0, 0.0]
        # On real Badger this gates initial e-paper full refresh; in the
        # emulator it's a no-op attribute apps still read/write.
        self.first_update = True

    @property
    def ticks(self):
        return int(_time.time() * 1000 - self._ticks_start_ms)

    @property
    def ticks_delta(self):
        # Approximate frame delta as 16ms (60fps); apps that care use ticks
        return 16

    def poll(self):
        st = get_state()
        buttons = st.get("buttons", {})
        new_held = set()
        for pin, btn in buttons.items():
            if pin in _PIN_TO_BUTTON and getattr(btn, "_pressed", False):
                new_held.add(_PIN_TO_BUTTON[pin])
        self._pressed = new_held - self._prev_held
        self._released = self._prev_held - new_held
        self._held = new_held
        self._prev_held = new_held

    def pressed(self, button=None):
        if button is None:
            return self._pressed
        return button in self._pressed

    def held(self, button=None):
        if button is None:
            return self._held
        return button in self._held

    def released(self, button=None):
        if button is None:
            return self._released
        return button in self._released

    def changed(self, button=None):
        ch = self._pressed | self._released
        if button is None:
            return ch
        return button in ch

    def clear(self):
        pass

    def update(self):
        display.update()
        self.poll()
        # Match vendor badge.update(): the first full refresh is done, so
        # apps gating on `badge.first_update` (e.g. the launcher's
        # `if changed or badge.first_update`) stop refreshing every frame.
        self.first_update = False

    def mode(self, mode_value=None):
        if mode_value is None:
            return self._mode
        self._mode = mode_value

    def resolution(self):
        return display.WIDTH, display.HEIGHT

    def battery_voltage(self):
        return 4.0

    def battery_level(self):
        return 80

    def usb_connected(self):
        return True

    def is_charging(self):
        return False

    def light_level(self):
        return 32768

    def disk_free(self, mountpoint="/"):
        return 8 * 1024 * 1024, 1024 * 1024, 7 * 1024 * 1024

    def pressed_to_wake(self, button):
        pass

    def sleep(self, ms=None):
        """Deep sleep — in the emulator, block until a button is pressed (or timeout)."""
        wait_for_button_or_alarm(timeout=ms if ms is not None else 30_000)

    def caselights(self, *args):
        """Set/get the four rear lighting zones (CL0..CL3).

        - caselights() returns the current 4-value list (0.0..1.0).
        - caselights(v) sets all four to v.
        - caselights(v0, v1, v2, v3) sets each individually.
        """
        if args:
            if len(args) == 1:
                self._case_light_values = [float(args[0])] * 4
            else:
                self._case_light_values = [float(a) for a in args[:4]]
            # Surface state for any future emulator panel.
            get_state()["case_lights"] = list(self._case_light_values)
        return list(self._case_light_values)


badge = _Badge()


class _IO:
    """Blinky-style input module.

    Upstream Blinky apps do `if io.BUTTON_A in io.pressed:` — `pressed`
    is a property returning a set, and BUTTON_* are attributes on the
    instance. The Tufty/Badger `badge` instance keeps `pressed` as a
    method, so we expose a separate `io` shim with property semantics
    for Blinky. Both back onto the same underlying button state.
    """

    BUTTON_A = BUTTON_A
    BUTTON_B = BUTTON_B
    BUTTON_C = BUTTON_C
    BUTTON_UP = BUTTON_UP
    BUTTON_DOWN = BUTTON_DOWN
    BUTTON_HOME = BUTTON_HOME

    @property
    def pressed(self):
        return badge._pressed

    @property
    def held(self):
        return badge._held

    @property
    def released(self):
        return badge._released

    @property
    def ticks(self):
        return badge.ticks

    def poll(self):
        badge.poll()


io = _IO()


# ── Main loop and helpers ────────────────────────────────────────────
class run:
    """Badgeware main loop — callable class so `run(update).result` works.

    Upstream exposes `run` as a class whose instance both drives the
    event loop AND stores `.result`, `.ticks`, `.duration`. We
    approximate: instantiating runs the loop synchronously; the
    instance retains the result of the final `update_fn()` call.
    """

    def __init__(self, *args, duration=None, init=None, on_exit=None, auto_clear=True):
        self.start = badge.ticks
        self.duration = duration
        self.result = None
        self._init = init
        self._on_exit = on_exit
        self._auto_clear = auto_clear
        if len(args) == 1 and callable(args[0]):
            self(args[0])

    @property
    def ticks(self):
        return badge.ticks - self.start

    @property
    def progress(self):
        return 0 if self.duration is None else self.ticks / self.duration

    def __call__(self, update_fn, init=None, on_exit=None, auto_clear=True):
        st = get_state()
        # Allow either ctor-supplied or call-supplied lifecycle hooks.
        init = init or self._init
        on_exit = on_exit or self._on_exit
        auto_clear = auto_clear if auto_clear is not None else self._auto_clear
        if init:
            init()
        # E-ink devices manage their own refresh timing (badge.update() is
        # explicit and slow ~500ms). Auto-flushing every frame would double
        # every refresh and cause constant e-ink animation flicker.
        dev = get_state().get("device")
        _is_eink = getattr(dev, 'is_eink', False)

        from emulator.mocks.base import honor_sleep
        try:
            while st.get("running", True):
                # Halt the app loop while the device is asleep (UI sleep button).
                honor_sleep()
                max_frames = st.get("max_frames", 0)
                if max_frames > 0 and st.get("frame_count", 0) >= max_frames:
                    break
                if auto_clear:
                    if badge.default_clear is not None:
                        builtins.screen.pen = badge.default_clear
                        builtins.screen.clear()
                    builtins.screen.pen = badge.default_pen
                badge.poll()
                result = update_fn()
                if result is not None:
                    self.result = result
                    return self
                if not _is_eink:
                    display.update()
                _time.sleep(0.016)
        except KeyboardInterrupt:
            pass
        finally:
            if on_exit:
                on_exit()
        return self


def launch(path):
    """Run an app by executing its __init__.py with badgeware builtins set.

    Upstream's launch does `__import__(path)` where path is a slash-name
    like "/system/apps/menu" — that works on MicroPython's file-based
    import. CPython treats slashes as invalid module names, so we
    resolve the path, put the (real, host-filesystem) directory on
    sys.path, and exec the __init__.py in a fresh globals dict.
    """
    import os
    import sys

    from emulator.mocks import _translate_path

    local_dir = _translate_path(path)
    if not os.path.isdir(local_dir):
        raise ModuleNotFoundError(f"launch: no app at {path} (resolved {local_dir})")

    init_py = os.path.join(local_dir, "__init__.py")
    if not os.path.exists(init_py):
        raise ModuleNotFoundError(f"launch: {path} has no __init__.py")

    os.chdir(path)
    sys.path.insert(0, local_dir)
    sys.path.insert(0, path)  # so `import sibling` works under MicroPython-style paths
    try:
        with open(init_py, "rb") as f:
            code = compile(f.read(), init_py, "exec")
        exec(code, {"__name__": "__main__", "__file__": init_py})
    finally:
        for p in (path, local_dir):
            if sys.path and sys.path[0] == p:
                sys.path.pop(0)


def reset():
    st = get_state()
    st["running"] = False


def clear_running():
    """Upstream resets the saved "running app" state to /system/apps/menu
    on cold boot. In the emulator this is a no-op — we don't persist."""
    pass


def _raw_held_buttons():
    """Snapshot the set of currently-held buttons straight from the shared
    button registry, without touching badge's edge state."""
    held = set()
    for pin, btn in get_state().get("buttons", {}).items():
        if pin in _PIN_TO_BUTTON and getattr(btn, "_pressed", False):
            held.add(_PIN_TO_BUTTON[pin])
    return held


def wait_for_button_or_alarm(timeout=30_000):
    """Block until a button state changes, the RTC alarm fires, or timeout.

    On real hardware this halts the CPU. In the emulator we sleep in
    short intervals so the pygame event loop (running in the main thread)
    can process input and the app thread wakes up when a button is pressed
    or the timeout expires.

    Crucially we must NOT call badge.poll() here. poll() diffs held vs
    prev_held to compute the pressed/released *edges*; if we polled to
    detect the wake, that same call would consume the edge and the
    run-loop's poll() at the top of the next frame would see nothing,
    so update() never observes the press. Instead we watch the raw button
    registry for any change and leave edge computation to the run loop.
    """
    import time as _t

    from emulator.mocks.base import honor_sleep

    # Headless mode has no pygame event loop, so no button press or sleep
    # toggle can ever arrive — blocking here would just stall every frame
    # for the full timeout. Return immediately, as before, so headless
    # runs (and scripts/smoke.sh) still progress at real speed.
    if get_state().get("headless"):
        return

    timeout_s = min(timeout / 1000.0, 30.0)
    deadline = _t.time() + timeout_s
    entry_held = _raw_held_buttons()
    while get_state().get("running", True):
        st = get_state()
        if st.get("sleeping"):
            # Device asleep: halt the idle wait, then resume cleanly once
            # woken (re-baseline held buttons and restart the timeout).
            honor_sleep()
            entry_held = _raw_held_buttons()
            deadline = _t.time() + timeout_s
            continue
        if st.pop("reset_requested", False):
            from emulator.mocks.machine import _MachineResetError
            raise _MachineResetError()
        if _raw_held_buttons() != entry_held:
            break
        if _t.time() >= deadline:
            break
        _t.sleep(0.02)


class _RTC:
    """Stub RTC — datetime + alarm methods used by Badger apps."""

    def __init__(self):
        self._alarm_set = False

    def datetime(self, dt=None):
        if dt is not None:
            return None
        import time as _t
        t = _t.localtime()
        # localtime() may return a struct_time or a plain tuple (MicroPython mock)
        if isinstance(t, tuple):
            return t[:7]
        return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday)

    def alarm_status(self):
        return False

    def clear_alarm(self):
        self._alarm_set = False

    def clear_alarm_flag(self):
        self._alarm_set = False

    def set_alarm(self, hours=0, minutes=0, seconds=0):
        self._alarm_set = True

    def update_time(self):
        pass

    def enable_timer_interrupt(self, enable=True):
        pass

    def set_timer(self, seconds):
        pass

    def clear_timer_flag(self):
        pass


rtc = _RTC()


def fatal_error(title, error):
    print(f"FATAL: {title}\n{error}")


# ── Builtins wiring ──────────────────────────────────────────────────
def install_badgeware():
    """Create the screen, bind the display, install builtins.

    Reads dimensions from the active emulator device so the same shim
    works for Tufty 2350 (320x240), Badger 2350 (296x128), and Blinky
    2350 (LED matrix). Safe to call after the picographics mock has
    been initialised — we just construct a fresh PicoGraphics for the
    framebuffer-backed `screen` and route updates through it.
    """
    dev = get_state().get("device")
    width = getattr(dev, "display_width", 320) if dev else 320
    height = getattr(dev, "display_height", 240) if dev else 240
    screen_image = image(width, height, is_screen=True)
    display.bind(screen_image)

    # E-ink devices (Badger) have no LORES half-res mode — they always
    # run at native resolution. Start in HIRES so screen.width/height
    # report the real panel dimensions rather than halved values.
    dev_name = type(dev).__name__.lower() if dev else ""
    _is_eink = getattr(dev, "is_eink", False) or "badger" in dev_name
    if _is_eink:
        badge._mode = HIRES | VSYNC
    # Stamp the flag on the screen object so width/height always return
    # native dimensions for e-ink, even if the app calls badge.mode(...)
    # with flags that don't include HIRES (e.g. FAST_UPDATE|NON_BLOCKING).
    screen_image._force_hires = _is_eink

    builtins.screen = screen_image
    builtins.display = display
    builtins.badge = badge
    builtins.rtc = rtc

    builtins.color = color
    builtins.brush = brush
    builtins.shape = shape
    builtins.image = image
    builtins.rect = rect
    builtins.vec2 = vec2
    builtins.mat3 = mat3
    builtins.SpriteSheet = SpriteSheet

    builtins.pixel_font = pixel_font
    builtins.rom_font = rom_font

    builtins.run = run
    builtins.launch = launch
    builtins.reset = reset
    builtins.clear_running = clear_running
    builtins.wait_for_button_or_alarm = wait_for_button_or_alarm
    builtins.fatal_error = fatal_error
    builtins.set_brightness = set_brightness
    builtins.mode = mode
    builtins.scroll_text = scroll_text
    builtins.load_font = load_font

    # `micropython` is a real module on-device; emulator apps just need
    # the name to exist for `import micropython` or attribute access.
    import micropython as _micropython_mod  # type: ignore
    builtins.micropython = _micropython_mod
    builtins.clamp = clamp
    builtins.rnd = rnd
    builtins.frnd = frnd
    builtins.State = State

    # Buttons / display modes
    builtins.BUTTON_A = BUTTON_A
    builtins.BUTTON_B = BUTTON_B
    builtins.BUTTON_C = BUTTON_C
    builtins.BUTTON_UP = BUTTON_UP
    builtins.BUTTON_DOWN = BUTTON_DOWN
    builtins.BUTTON_HOME = BUTTON_HOME
    builtins.HIRES = HIRES
    builtins.LORES = LORES
    builtins.VSYNC = VSYNC
    builtins.FAST_UPDATE = FAST_UPDATE
    builtins.FULL_UPDATE = FULL_UPDATE
    builtins.MEDIUM_UPDATE = MEDIUM_UPDATE
    builtins.NON_BLOCKING = NON_BLOCKING
    builtins.DITHER = DITHER
    builtins.OFF = image.OFF
    builtins.X2 = image.X2
    builtins.X4 = image.X4

    # file_exists / is_dir — used by the upstream launcher menu
    import os as _os

    def file_exists(p):
        try:
            from emulator.mocks import _translate_path
            return _os.path.exists(_translate_path(p))
        except Exception:  # noqa: BLE001
            return False

    def is_dir(p):
        try:
            from emulator.mocks import _translate_path
            return _os.path.isdir(_translate_path(p))
        except Exception:  # noqa: BLE001
            return False

    builtins.file_exists = file_exists
    builtins.is_dir = is_dir
    # Also expose at module level so `from badgeware import is_dir` works.
    import sys as _sys
    _mod = _sys.modules[__name__]
    _mod.file_exists = file_exists
    _mod.is_dir = is_dir

    # Pimoroni's `secrets` module wraps the user's /system/secrets.py
    # and adds a `require(*keys)` validator. CPython has a stdlib
    # `secrets` for cryptographic randomness — we monkey-patch to add
    # `require` rather than shadow the whole module. Default fake WiFi
    # credentials so smoke-testing apps that gate on require() can
    # proceed past the check (the wifi mock returns "connected").
    import secrets as _secrets

    _secrets.WIFI_SSID = getattr(_secrets, "WIFI_SSID", "emulator")
    _secrets.WIFI_PASSWORD = getattr(_secrets, "WIFI_PASSWORD", "emulator")
    _secrets.WIFI_COUNTRY = getattr(_secrets, "WIFI_COUNTRY", "US")
    # Default location (London) so weather/location apps get a valid API response
    # instead of "emulator" which Open-Meteo rejects with a parse error.
    _secrets.LAT = getattr(_secrets, "LAT", 51.5074)
    _secrets.LON = getattr(_secrets, "LON", -0.1278)

    def _require(*keys):
        # Lenient in the emulator: any key the user hasn't set gets a
        # placeholder rather than aborting the app, so smoke tests on
        # weather/clock/etc. proceed past the gate.
        for k in keys:
            if getattr(_secrets, k, None) in (None, ""):
                setattr(_secrets, k, "emulator")

    if not hasattr(_secrets, "require"):
        _secrets.require = _require
