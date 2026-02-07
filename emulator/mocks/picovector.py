"""Mock implementation of PicoVector for vector graphics.

PicoVector is a vector graphics library that draws anti-aliased shapes
using PicoGraphics as the rendering backend.
"""

import math
from typing import List, Tuple, Optional, Any
from emulator import get_state


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


class PicoVector:
    """Vector graphics renderer using PicoGraphics."""

    def __init__(self, display):
        """Initialize with a PicoGraphics display."""
        self._display = display
        self._transform = Transform()
        self._antialiasing = ANTIALIAS_NONE

        # Font settings
        self._font_file = None
        self._font_size = 16
        self._font_word_spacing = 4
        self._font_letter_spacing = 1
        self._font_line_height = 1.2
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

        state = get_state()
        if state.get("trace"):
            print(f"[PicoVector] set_font({filename}, {size})")

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

    def measure_text(self, text: str, x: float = 0, y: float = 0,
                     angle: float = None) -> Tuple[float, float, float, float]:
        """Measure text dimensions.

        Returns (x, y, width, height).
        """
        # Simple estimation based on font size
        char_width = self._font_size * 0.6
        char_height = self._font_size

        lines = text.split('\n')
        max_width = max(len(line) for line in lines) * (char_width + self._font_letter_spacing)
        total_height = len(lines) * char_height * self._font_line_height

        return (x, y, max_width, total_height)

    def text(self, text: str, x: float, y: float, angle: float = None,
             max_width: float = 0, max_height: float = 0):
        """Draw text at position.

        Note: In the emulator, this falls back to PicoGraphics text rendering
        since we don't have .af font file parsing.
        """
        # Apply transform
        tx, ty = self._transform.apply(x, y)

        # Calculate scale from font size (bitmap8 is 8px tall)
        scale = self._font_size / 8

        # Use PicoGraphics text rendering
        self._display.text(text, int(tx), int(ty), scale=scale)

        state = get_state()
        if state.get("trace"):
            print(f"[PicoVector] text('{text[:20]}...', {x}, {y})")
