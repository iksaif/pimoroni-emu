"""Mock implementation of PicoVector for vector graphics.

PicoVector is a vector graphics library that draws anti-aliased shapes
using PicoGraphics as the rendering backend.
"""

import math
import os
import struct
import sys
from typing import List, Tuple, Optional, Any
from emulator import get_state

try:
    import svgelements
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False


# Anti-aliasing modes
ANTIALIAS_NONE = 0
ANTIALIAS_FAST = 1  # 4x
ANTIALIAS_BEST = 2  # 16x


class Transform:
    """Transformation matrix for scaling, rotating, and translating shapes."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset to identity transform."""
        # 3x3 identity matrix stored as flat list
        self._matrix = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ]

    def rotate(self, angle: float, center: Tuple[float, float] = (0, 0)):
        """Rotate by angle degrees around center point."""
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        cx, cy = center

        # Translate to origin, rotate, translate back
        self.translate(-cx, -cy)
        rotation = [
            cos_a, -sin_a, 0.0,
            sin_a, cos_a, 0.0,
            0.0, 0.0, 1.0
        ]
        self._multiply(rotation)
        self.translate(cx, cy)

    def scale(self, scale_x: float, scale_y: float = None):
        """Apply scaling."""
        if scale_y is None:
            scale_y = scale_x
        scale_matrix = [
            scale_x, 0.0, 0.0,
            0.0, scale_y, 0.0,
            0.0, 0.0, 1.0
        ]
        self._multiply(scale_matrix)

    def translate(self, x: float, y: float):
        """Apply translation."""
        trans_matrix = [
            1.0, 0.0, x,
            0.0, 1.0, y,
            0.0, 0.0, 1.0
        ]
        self._multiply(trans_matrix)

    def matrix(self, values: List[float]):
        """Apply arbitrary 3x3 matrix transformation."""
        if len(values) == 9:
            self._multiply(values)

    def _multiply(self, other: List[float]):
        """Multiply current matrix by another."""
        a = self._matrix
        b = other
        result = [0.0] * 9

        for i in range(3):
            for j in range(3):
                for k in range(3):
                    result[i * 3 + j] += a[i * 3 + k] * b[k * 3 + j]

        self._matrix = result

    def apply(self, x: float, y: float) -> Tuple[float, float]:
        """Apply transform to a point."""
        m = self._matrix
        new_x = m[0] * x + m[1] * y + m[2]
        new_y = m[3] * x + m[4] * y + m[5]
        return (new_x, new_y)


class Polygon:
    """A collection of paths that make up a shape."""

    def __init__(self):
        self._paths: List[List[Tuple[float, float]]] = []
        self._stroke = 0

    @classmethod
    def from_svg(cls, filename: str) -> "Polygon":
        """Load polygon paths from an SVG file.

        This is an emulator extension — upstream PicoVector has no SVG support.
        """
        resolved = _resolve_file(filename)
        if resolved is None:
            raise FileNotFoundError(f"SVG file not found: {filename}")

        paths = _load_svg(resolved)
        poly = cls()
        poly._paths = paths

        state = get_state()
        if state.get("trace"):
            print(f"[PicoVector] Polygon.from_svg({filename}) - {len(paths)} paths loaded")

        return poly

    def path(self, *points):
        """Add a path from a list of points."""
        if len(points) >= 3:
            self._paths.append(list(points))
        return self

    def line(self, x1: float, y1: float, x2: float, y2: float, thickness: float = 1):
        """Create a line with given thickness."""
        # Convert line to a thin rectangle
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return self

        # Perpendicular direction
        px = -dy / length * thickness / 2
        py = dx / length * thickness / 2

        self._paths.append([
            (x1 + px, y1 + py),
            (x2 + px, y2 + py),
            (x2 - px, y2 - py),
            (x1 - px, y1 - py),
        ])
        return self

    def rectangle(self, x: float, y: float, w: float, h: float,
                  corners: Tuple[float, float, float, float] = (0, 0, 0, 0),
                  stroke: float = 0):
        """Create a rectangle with optional rounded corners."""
        self._stroke = stroke

        if all(c == 0 for c in corners):
            # Simple rectangle
            if stroke > 0:
                # Stroke: outer and inner rectangles
                self._paths.append([
                    (x, y), (x + w, y), (x + w, y + h), (x, y + h)
                ])
                self._paths.append([
                    (x + stroke, y + stroke),
                    (x + w - stroke, y + stroke),
                    (x + w - stroke, y + h - stroke),
                    (x + stroke, y + h - stroke)
                ])
            else:
                self._paths.append([
                    (x, y), (x + w, y), (x + w, y + h), (x, y + h)
                ])
        else:
            # Rounded corners - approximate with segments
            points = self._rounded_rect_points(x, y, w, h, corners)
            self._paths.append(points)
        return self

    def _rounded_rect_points(self, x: float, y: float, w: float, h: float,
                             corners: Tuple[float, float, float, float]) -> List[Tuple[float, float]]:
        """Generate points for a rounded rectangle."""
        r1, r2, r3, r4 = corners  # top-left, top-right, bottom-right, bottom-left
        points = []
        segments = 8  # segments per corner

        # Top edge (left to right)
        if r1 > 0:
            for i in range(segments + 1):
                angle = math.pi + (math.pi / 2) * (i / segments)
                points.append((x + r1 + r1 * math.cos(angle), y + r1 + r1 * math.sin(angle)))
        else:
            points.append((x, y))

        if r2 > 0:
            for i in range(segments + 1):
                angle = -math.pi / 2 + (math.pi / 2) * (i / segments)
                points.append((x + w - r2 + r2 * math.cos(angle), y + r2 + r2 * math.sin(angle)))
        else:
            points.append((x + w, y))

        # Right edge, bottom-right corner
        if r3 > 0:
            for i in range(segments + 1):
                angle = 0 + (math.pi / 2) * (i / segments)
                points.append((x + w - r3 + r3 * math.cos(angle), y + h - r3 + r3 * math.sin(angle)))
        else:
            points.append((x + w, y + h))

        # Bottom edge, bottom-left corner
        if r4 > 0:
            for i in range(segments + 1):
                angle = math.pi / 2 + (math.pi / 2) * (i / segments)
                points.append((x + r4 + r4 * math.cos(angle), y + h - r4 + r4 * math.sin(angle)))
        else:
            points.append((x, y + h))

        return points

    def regular(self, x: float, y: float, radius: float, sides: int, stroke: float = 0):
        """Create a regular polygon."""
        self._stroke = stroke
        points = []
        for i in range(sides):
            angle = (2 * math.pi * i / sides) - math.pi / 2
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.append((px, py))
        self._paths.append(points)

        if stroke > 0:
            # Add inner polygon for stroke
            inner_points = []
            inner_radius = radius - stroke
            for i in range(sides):
                angle = (2 * math.pi * i / sides) - math.pi / 2
                px = x + inner_radius * math.cos(angle)
                py = y + inner_radius * math.sin(angle)
                inner_points.append((px, py))
            self._paths.append(inner_points)
        return self

    def circle(self, x: float, y: float, radius: float, stroke: float = 0):
        """Create a circle."""
        # Approximate with regular polygon - more sides for larger circles
        sides = max(16, int(radius * 2))
        self.regular(x, y, radius, sides, stroke)
        return self

    def arc(self, x: float, y: float, radius: float,
            from_angle: float, to_angle: float, stroke: float = 0):
        """Create an arc."""
        self._stroke = stroke
        points = []

        # Convert to radians
        start = math.radians(from_angle)
        end = math.radians(to_angle)

        # Number of segments based on arc length
        arc_length = abs(end - start)
        segments = max(8, int(arc_length * radius / 4))

        # Outer arc
        for i in range(segments + 1):
            angle = start + (end - start) * (i / segments)
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.append((px, py))

        if stroke > 0:
            # Inner arc (reverse direction)
            inner_radius = radius - stroke
            for i in range(segments, -1, -1):
                angle = start + (end - start) * (i / segments)
                px = x + inner_radius * math.cos(angle)
                py = y + inner_radius * math.sin(angle)
                points.append((px, py))
        else:
            # Fill to center
            points.append((x, y))

        self._paths.append(points)
        return self

    def star(self, x: float, y: float, num_points: int,
             inner_radius: float, outer_radius: float, stroke: float = 0):
        """Create a star."""
        self._stroke = stroke
        points = []

        for i in range(num_points * 2):
            angle = (math.pi * i / num_points) - math.pi / 2
            if i % 2 == 0:
                r = outer_radius
            else:
                r = inner_radius
            px = x + r * math.cos(angle)
            py = y + r * math.sin(angle)
            points.append((px, py))

        self._paths.append(points)
        return self


def _linearize_path(path, tolerance: float = 1.0) -> List[List[Tuple[float, float]]]:
    """Convert an svgelements Path into lists of (x, y) points.

    Walks each sub-path/segment, linearising curves via point sampling.
    Returns one point list per sub-path (separated by Move commands).
    """
    subpaths: List[List[Tuple[float, float]]] = []
    current: List[Tuple[float, float]] = []

    for seg in path.segments():
        seg_type = type(seg).__name__

        if seg_type == "Move":
            # Start a new sub-path
            if len(current) >= 3:
                subpaths.append(current)
            current = [(float(seg.end.real), float(seg.end.imag))]

        elif seg_type == "Close":
            if current and len(current) >= 3:
                subpaths.append(current)
            current = []

        elif seg_type == "Line":
            current.append((float(seg.end.real), float(seg.end.imag)))

        elif seg_type in ("CubicBezier", "QuadraticBezier", "Arc"):
            # Estimate number of samples from segment length
            try:
                length = seg.length()
            except (ZeroDivisionError, ValueError):
                length = 10.0
            steps = max(4, int(length / tolerance))
            for i in range(1, steps + 1):
                t = i / steps
                pt = seg.point(t)
                current.append((float(pt.real), float(pt.imag)))

        else:
            # Unknown segment type – try to grab the endpoint
            if hasattr(seg, "end"):
                current.append((float(seg.end.real), float(seg.end.imag)))

    if len(current) >= 3:
        subpaths.append(current)

    return subpaths


def _load_svg(filepath: str) -> List[List[Tuple[float, float]]]:
    """Parse an SVG file and return polygon paths.

    Uses svgelements to parse shapes, paths, transforms, and viewBox.
    All curves are linearised into point lists suitable for scanline fill.
    """
    if not _HAS_SVG:
        raise ImportError(
            "svgelements is required for SVG loading. "
            "Install it with: pip install svgelements"
        )

    svg = svgelements.SVG.parse(filepath)
    all_paths: List[List[Tuple[float, float]]] = []

    for element in svg.elements():
        # Skip non-shape elements
        if not isinstance(element, svgelements.Shape):
            continue

        # Convert any shape to a Path (handles rect, circle, ellipse, polygon, etc.)
        try:
            path = abs(svgelements.Path(element))
        except (ValueError, AttributeError):
            continue

        subpaths = _linearize_path(path)
        all_paths.extend(subpaths)

    return all_paths


def _resolve_file(filename: str) -> Optional[str]:
    """Resolve a filename relative to app dir, cwd, or sys.path."""
    search_paths = []
    state = get_state()
    app_path = state.get("app_path")
    if app_path:
        search_paths.append(os.path.dirname(os.path.abspath(app_path)))
    if sys.path:
        search_paths.append(sys.path[0])
    search_paths.append(os.getcwd())

    for base in search_paths:
        candidate = os.path.join(base, filename)
        if os.path.isfile(candidate):
            return candidate

    # Try as absolute / relative to cwd
    if os.path.isfile(filename):
        return filename

    return None


def _load_af_font(filepath: str) -> Optional[dict]:
    """Parse an Alright Fonts (.af) binary file.

    Returns a dict mapping codepoint -> glyph data, or None on failure.
    Format reference: vendor/pimoroni-pico/libraries/pico_vector/alright-fonts.h
    """
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except (OSError, IOError):
        return None

    if len(data) < 12 or data[:4] != b"af!?":
        return None

    flags, glyph_count, path_count, point_count = struct.unpack_from(">HHHH", data, 4)
    flag_16bit = flags & 0x0001

    offset = 12
    glyphs = []
    for _ in range(glyph_count):
        if offset + 8 > len(data):
            return None
        cp, gx, gy, gw, gh, advance, pc = struct.unpack_from(">HbbBBBB", data, offset)
        glyphs.append({
            "codepoint": cp, "x": gx, "y": gy, "w": gw, "h": gh,
            "advance": advance, "path_count": pc, "paths": [],
        })
        offset += 8

    # Read path point counts
    path_point_counts = []
    for _ in range(path_count):
        if flag_16bit:
            if offset + 2 > len(data):
                return None
            (pc,) = struct.unpack_from(">H", data, offset)
            offset += 2
        else:
            if offset + 1 > len(data):
                return None
            pc = data[offset]
            offset += 1
        path_point_counts.append(pc)

    # Read all points
    all_points = []
    for _ in range(point_count):
        if offset + 2 > len(data):
            return None
        px, py = data[offset], data[offset + 1]
        all_points.append((float(px), float(py)))
        offset += 2

    # Assign paths and points to glyphs
    path_idx = 0
    point_idx = 0
    for glyph in glyphs:
        for _ in range(glyph["path_count"]):
            if path_idx >= len(path_point_counts):
                break
            n_pts = path_point_counts[path_idx]
            path_idx += 1
            pts = all_points[point_idx:point_idx + n_pts]
            point_idx += n_pts
            glyph["paths"].append(pts)

    # Build lookup dict
    font = {}
    for g in glyphs:
        font[g["codepoint"]] = g
    return font


class PicoVector:
    """Vector graphics renderer using PicoGraphics."""

    def __init__(self, display):
        """Initialize with a PicoGraphics display."""
        self._display = display
        self._transform = Transform()
        self._antialiasing = ANTIALIAS_NONE

        # Font settings (upstream defaults from pico_vector.hpp)
        self._font_file = None
        self._af_font = None
        self._font_size = 48
        self._font_word_spacing = 200  # percentage
        self._font_letter_spacing = 95  # percentage
        self._font_line_height = 110  # percentage
        self._font_align = 0  # 0=left, 1=center, 2=right

        state = get_state()
        if state.get("trace"):
            print("[PicoVector] Initialized")

    def set_transform(self, transform: Transform):
        """Set the current transform."""
        self._transform = transform

    def set_antialiasing(self, mode: int):
        """Set anti-aliasing mode."""
        self._antialiasing = mode

    def draw(self, polygon: Polygon):
        """Draw a polygon to the display."""
        if not polygon._paths:
            return

        for path in polygon._paths:
            if len(path) < 3:
                continue

            # Apply transform to all points
            transformed = [self._transform.apply(x, y) for x, y in path]

            # Convert to integer coordinates for PicoGraphics
            int_points = [(int(x), int(y)) for x, y in transformed]

            # Draw filled polygon using PicoGraphics
            self._fill_polygon(int_points)

    def _fill_polygon(self, points: List[Tuple[int, int]]):
        """Fill a polygon using scanline algorithm."""
        if len(points) < 3:
            return

        # Find bounding box
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)

        # Clip to display bounds
        width, height = self._display.get_bounds()
        min_y = max(0, min_y)
        max_y = min(height - 1, max_y)
        min_x = max(0, min_x)
        max_x = min(width - 1, max_x)

        # Scanline fill
        n = len(points)
        for y in range(min_y, max_y + 1):
            intersections = []

            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]

                if y1 == y2:
                    continue

                if min(y1, y2) <= y < max(y1, y2):
                    # Calculate intersection
                    x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                    intersections.append(int(x))

            intersections.sort()

            # Fill between pairs of intersections
            for i in range(0, len(intersections) - 1, 2):
                x_start = max(min_x, intersections[i])
                x_end = min(max_x, intersections[i + 1])
                for x in range(x_start, x_end + 1):
                    self._display.pixel(x, y)

    # Font methods
    def set_font(self, filename: str, size: float = None):
        """Set the font file and optionally size."""
        self._font_file = filename
        if size is not None:
            self._font_size = size

        # Try to load .af font file
        self._af_font = None
        if filename.endswith(".af"):
            resolved = _resolve_file(filename)
            if resolved is not None:
                self._af_font = _load_af_font(resolved)

        state = get_state()
        if state.get("trace"):
            loaded = "loaded" if self._af_font else "not found"
            print(f"[PicoVector] set_font({filename}, {size}) - {loaded}")

        return self._af_font is not None

    def set_font_size(self, size: float):
        """Set font size."""
        self._font_size = size

    def set_font_word_spacing(self, spacing: float):
        """Set word spacing."""
        self._font_word_spacing = spacing

    def set_font_letter_spacing(self, spacing: float):
        """Set letter spacing."""
        self._font_letter_spacing = spacing

    def set_font_line_height(self, height: float):
        """Set line height multiplier."""
        self._font_line_height = height

    def set_font_align(self, align: int):
        """Set text alignment (0=left, 1=center, 2=right)."""
        self._font_align = align

    def _get_line_width(self, line: str) -> float:
        """Compute line width in glyph coordinate space (pre-scale)."""
        width = 0.0
        for ch in line:
            cp = ord(ch)
            glyph = self._af_font.get(cp)
            if not glyph:
                continue
            if ch == ' ':
                width += (glyph["advance"] * self._font_word_spacing) / 100.0
            else:
                width += (glyph["advance"] * self._font_letter_spacing) / 100.0
        return width

    def measure_text(self, text: str, x: float = 0, y: float = 0,
                     angle: float = None) -> Tuple[float, float, float, float]:
        """Measure text dimensions. Returns (x, y, width, height)."""
        if not self._af_font:
            char_width = self._font_size * 0.6
            char_height = self._font_size
            lines = text.split('\n')
            max_width = max(len(line) for line in lines) * (char_width + self._font_letter_spacing)
            total_height = len(lines) * char_height * (self._font_line_height / 100.0)
            return (x, y, max_width, total_height)

        scale = self._font_size / 128.0
        line_height = (self._font_line_height * 128.0) / 100.0

        lines = text.split('\n')
        max_w = 0.0
        for line in lines:
            w = self._get_line_width(line)
            if w > max_w:
                max_w = w

        total_w = max_w * scale
        total_h = len(lines) * line_height * scale

        return (x, y, total_w, total_h)

    def text(self, text: str, x: float, y: float, angle: float = None,
             max_width: float = 0, max_height: float = 0):
        """Draw text at position using .af font glyphs or bitmap fallback."""
        if not self._af_font:
            # Bitmap fallback
            tx, ty = self._transform.apply(x, y)
            scale = self._font_size / 8
            self._display.text(text, int(tx), int(ty), scale=scale)
            return

        scale = self._font_size / 128.0
        line_height_glyph = (self._font_line_height * 128.0) / 100.0

        # Build per-text transform: identity -> rotate(angle) -> translate(x, y)
        text_transform = Transform()
        if angle is not None:
            text_transform.rotate(angle)
        text_transform.translate(x, y)

        lines = text.split('\n')

        # Compute max line width for alignment (matching upstream)
        max_line_w = 0.0
        if max_width > 0:
            max_line_w = max_width / scale
        else:
            for line in lines:
                w = self._get_line_width(line)
                if w > max_line_w:
                    max_line_w = w

        max_h = max_height / scale if max_height > 0 else float('inf')

        caret_y = 0.0
        for line in lines:
            if caret_y + line_height_glyph > max_h:
                break
            line_width = self._get_line_width(line)
            caret_x = 0.0

            for ch in line:
                cp = ord(ch)
                glyph = self._af_font.get(cp)
                if not glyph:
                    continue

                # Build caret transform matching upstream:
                # caret_transform = text_transform * scale(s,s) * translate(cx, cy + align_offset)
                caret = Transform()
                caret._matrix = list(text_transform._matrix)
                caret.scale(scale, scale)
                caret.translate(caret_x, caret_y)

                # Alignment offset (in glyph coordinate space)
                if self._font_align == 1:  # center
                    caret.translate((max_line_w - line_width) / 2, 0)
                elif self._font_align == 2:  # right
                    caret.translate(max_line_w - line_width, 0)

                # Compose with the global set_transform
                final = Transform()
                final._matrix = list(self._transform._matrix)
                final._multiply(caret._matrix)

                # Render each path in the glyph
                for path_points in glyph["paths"]:
                    if len(path_points) < 3:
                        continue
                    transformed = [final.apply(px, py) for px, py in path_points]
                    int_points = [(int(px), int(py)) for px, py in transformed]
                    self._fill_polygon(int_points)

                # Advance caret
                if ch == ' ':
                    caret_x += (glyph["advance"] * self._font_word_spacing) / 100.0
                else:
                    caret_x += (glyph["advance"] * self._font_letter_spacing) / 100.0

            caret_y += line_height_glyph

        state = get_state()
        if state.get("trace"):
            print(f"[PicoVector] text('{text[:20]}...', {x}, {y})")
