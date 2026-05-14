"""CRT terminal theme — palette + draw helpers.

Layout constants are computed from the active device bounds: the Presto's
480x480 gets large fonts and a thick touch footer; the Tufty 2350's 320x240
gets the original design's scale with a slim label-only footer.

Call `init(device)` once at startup, then everywhere else `theme.WIDTH`
etc. read the per-device values.
"""

import time

# MicroPython's time.time() is integer-seconds; ticks_ms gives sub-second
# resolution for animations. Fall back to wall-clock on CPython.
_HAS_TICKS_MS = hasattr(time, "ticks_ms")


def _ms_phase(period_ms):
    """Return phase in [0, 1) over a period_ms cycle."""
    if _HAS_TICKS_MS:
        return (time.ticks_ms() % period_ms) / period_ms
    return (time.time() % (period_ms / 1000.0)) / (period_ms / 1000.0)

# ─── Palette (CRT green-phosphor) ──────────────────────────────────────
BG     = (2, 6, 4)
FG     = (52, 255, 122)
DIM    = (29, 138, 68)
WARN   = (255, 204, 51)
DOWN   = (255, 80, 80)
SCAN   = (12, 24, 16)


# ─── Per-device layout (populated by init()) ───────────────────────────
DEVICE        = None
WIDTH         = 0
HEIGHT        = 0
PADDING_X     = 10
HEADER_H      = 22
FOOTER_H      = 20
BODY_TOP      = 22
BODY_BOTTOM   = 220

SCALE_HERO    = 4
SCALE_BODY    = 2
SCALE_TINY    = 1

ROW_LABEL_W   = 36
HEATMAP_CELL_H = 20
PLOT_HEIGHT   = 60

TAB_W         = 0
SHOW_TAB_BOX  = False     # only Presto draws a touch box around the active tab


_PEN_CACHE = {}


def init(device):
    """Configure layout for the given Device instance."""
    global DEVICE, WIDTH, HEIGHT, PADDING_X, HEADER_H, FOOTER_H
    global BODY_TOP, BODY_BOTTOM
    global SCALE_HERO, SCALE_BODY, SCALE_TINY
    global ROW_LABEL_W, HEATMAP_CELL_H, PLOT_HEIGHT
    global TAB_W, SHOW_TAB_BOX

    DEVICE = device
    WIDTH  = device.width
    HEIGHT = device.height
    _PEN_CACHE.clear()

    if device.has_touch:
        # Presto (480x480) — touch tabs, large fonts
        PADDING_X      = 14
        HEADER_H       = 36
        FOOTER_H       = 66
        SCALE_HERO     = 6
        SCALE_BODY     = 2
        SCALE_TINY     = 1
        ROW_LABEL_W    = 56
        HEATMAP_CELL_H = 34
        PLOT_HEIGHT    = 110
        SHOW_TAB_BOX   = True
    else:
        # Tufty (320x240) — physical buttons, compact fonts
        PADDING_X      = 8
        HEADER_H       = 22
        FOOTER_H       = 20
        SCALE_HERO     = 4
        SCALE_BODY     = 2
        SCALE_TINY     = 1
        ROW_LABEL_W    = 28
        HEATMAP_CELL_H = 18
        PLOT_HEIGHT    = 58
        SHOW_TAB_BOX   = False

    BODY_TOP    = HEADER_H
    BODY_BOTTOM = HEIGHT - FOOTER_H
    TAB_W       = WIDTH // 3


# ─── Pen cache (PicoGraphics pens are integers) ─────────────────────────


def pen(display, rgb):
    p = _PEN_CACHE.get(rgb)
    if p is None:
        p = display.create_pen(*rgb)
        _PEN_CACHE[rgb] = p
    return p


# ─── Drawing helpers ───────────────────────────────────────────────────


def dashed_hline(display, y, x0=None, x1=None, on=4, off=6, colour=None):
    if x0 is None:
        x0 = PADDING_X
    if x1 is None:
        x1 = WIDTH - PADDING_X
    if colour is None:
        colour = DIM
    display.set_pen(pen(display, colour))
    x = x0
    period = on + off
    while x < x1:
        display.rectangle(x, y, min(on, x1 - x), 1)
        x += period


def dashed_vline(display, x, y0, y1, on=4, off=6, colour=None):
    if colour is None:
        colour = DIM
    display.set_pen(pen(display, colour))
    y = y0
    period = on + off
    while y < y1:
        display.rectangle(x, y, 1, min(on, y1 - y))
        y += period


def status_colour(status):
    if status == "ok":
        return FG
    if status == "warn":
        return WARN
    if status == "down":
        return DOWN
    return DIM


def status_glyph(status):
    if status == "ok":
        return "* OK"
    if status == "warn":
        return "^ WARN"
    if status == "down":
        return "x DOWN"
    return "? --"


def status_pill(display, x_right, y, status, height=None):
    if height is None:
        height = 22 if DEVICE.has_touch else 14
    label = status_glyph(status)
    text_w = display.measure_text(label, scale=SCALE_BODY)
    pad_x = 8 if DEVICE.has_touch else 4
    w = text_w + pad_x * 2
    x = x_right - w
    col = status_colour(status)
    display.set_pen(pen(display, col))
    display.rectangle(x, y, w, 1)
    display.rectangle(x, y + height - 1, w, 1)
    display.rectangle(x, y, 1, height)
    display.rectangle(x + w - 1, y, 1, height)
    text_y = y + (height - 8 * SCALE_BODY) // 2
    display.text(label, x + pad_x, text_y, scale=SCALE_BODY)
    return x


def cursor_visible():
    return _ms_phase(1000) < 0.5


# ─── Header / footer ───────────────────────────────────────────────────


def draw_header(display, mode_text, clock_text):
    dashed_hline(display, HEADER_H - 1, x0=0, x1=WIDTH)
    title = "> WIFI HEALTH . " + mode_text
    display.set_pen(pen(display, FG))
    display.text(title, PADDING_X, (HEADER_H - 8 * SCALE_BODY) // 2,
                 scale=SCALE_BODY)
    title_w = display.measure_text(title, scale=SCALE_BODY)
    if cursor_visible():
        cw = 10 if DEVICE.has_touch else 6
        cy = (HEADER_H - 8 * SCALE_BODY) // 2
        display.rectangle(PADDING_X + title_w + 4, cy, cw, 8 * SCALE_BODY)
    display.set_pen(pen(display, DIM))
    clock_w = display.measure_text(clock_text, scale=SCALE_BODY)
    display.text(clock_text, WIDTH - PADDING_X - clock_w,
                 (HEADER_H - 8 * SCALE_BODY) // 2, scale=SCALE_BODY)


TABS = [
    ("CURRENT", "current"),
    ("LOG 24H", "log"),
    ("CFG",     "settings"),
]


def draw_footer(display, active):
    y = BODY_BOTTOM
    dashed_hline(display, y, x0=0, x1=WIDTH)

    regions = []
    for i, (label, key) in enumerate(TABS):
        tx = i * TAB_W
        if SHOW_TAB_BOX and key == active:
            display.set_pen(pen(display, FG))
            display.rectangle(tx + 4, y + 6, TAB_W - 8, 1)
            display.rectangle(tx + 4, y + FOOTER_H - 2, TAB_W - 8, 1)
            display.rectangle(tx + 4, y + 6, 1, FOOTER_H - 8)
            display.rectangle(tx + TAB_W - 5, y + 6, 1, FOOTER_H - 8)

        prefix = "[{}]".format("ABC"[i])
        prefix_w = display.measure_text(prefix, scale=SCALE_BODY)
        label_w = display.measure_text(label, scale=SCALE_BODY)
        gap = 6 if DEVICE.has_touch else 3
        total_w = prefix_w + gap + label_w
        x_text = tx + (TAB_W - total_w) // 2
        y_text = y + (FOOTER_H - 8 * SCALE_BODY) // 2

        active_here = (key == active)
        display.set_pen(pen(display, FG))
        display.text(prefix, x_text, y_text, scale=SCALE_BODY)
        display.set_pen(pen(display, FG if active_here else DIM))
        display.text(label, x_text + prefix_w + gap, y_text, scale=SCALE_BODY)

        regions.append((key, tx, y, TAB_W, FOOTER_H))

    if DEVICE.has_touch:
        for i in range(1, len(TABS)):
            dashed_vline(display, i * TAB_W, y + 4, y + FOOTER_H - 4)

    return regions
