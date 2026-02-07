"""Mock implementation of Pimoroni's picographics module.

This is the core display API used by all Pimoroni devices.
"""

from typing import Optional, Tuple, List
import math
from emulator import get_state, get_display
from emulator.mocks.fonts import get_font, BitmapFont


# Display types
DISPLAY_TUFTY_2350 = 0
DISPLAY_PRESTO = 1
DISPLAY_BLINKY = 2
DISPLAY_PICO_DISPLAY = 3
DISPLAY_PICO_DISPLAY_2 = 4
DISPLAY_PICO_W_EXPLORER = 5
DISPLAY_ENVIRO_PLUS = 6
DISPLAY_LCD_240X240 = 7
DISPLAY_ROUND_LCD_240X240 = 8
DISPLAY_PICO_EXPLORER = 9
DISPLAY_INKY_PACK = 10
DISPLAY_INKY_FRAME = 11
DISPLAY_INKY_FRAME_4 = 12
DISPLAY_GALACTIC_UNICORN = 13
DISPLAY_COSMIC_UNICORN = 14
DISPLAY_STELLAR_UNICORN = 15
DISPLAY_INTERSTATE75_32X32 = 16
DISPLAY_INTERSTATE75_64X32 = 17
DISPLAY_INTERSTATE75_64X64 = 18
DISPLAY_INTERSTATE75_128X32 = 19
DISPLAY_INTERSTATE75_128X64 = 20
DISPLAY_INTERSTATE75_128X128 = 21
DISPLAY_INTERSTATE75_192X64 = 22
DISPLAY_INTERSTATE75_256X64 = 23
DISPLAY_BADGER_2350 = 24
DISPLAY_INKY_FRAME_7 = 25
DISPLAY_INKY_FRAME_4 = 26
DISPLAY_INKY_FRAME_5 = 27
DISPLAY_GENERIC = 100  # Generic display with custom width/height

# Pen types (color modes)
PEN_1BIT = 0
PEN_P4 = 1
PEN_P8 = 2
PEN_RGB332 = 3
PEN_RGB565 = 4
PEN_RGB888 = 5

# Display dimensions
_DISPLAY_SIZES = {
    DISPLAY_TUFTY_2350: (320, 240),
    DISPLAY_PRESTO: (480, 480),
    DISPLAY_BLINKY: (44, 20),  # Estimated LED matrix
    DISPLAY_PICO_DISPLAY: (240, 135),
    DISPLAY_BADGER_2350: (296, 128),  # E-ink badge
    DISPLAY_PICO_DISPLAY_2: (320, 240),
    DISPLAY_LCD_240X240: (240, 240),
    # Inky Frame e-ink displays
    DISPLAY_INKY_FRAME_7: (800, 480),   # 7.3" Spectra 6
    DISPLAY_INKY_FRAME_5: (600, 448),   # 5.8" ACeP 7-color
    DISPLAY_INKY_FRAME_4: (640, 400),   # 4.0" ACeP 7-color
}


class PicoGraphics:
    """Main graphics class for Pimoroni displays."""

    def __init__(
        self,
        display: int,
        rotate: int = 0,
        bus=None,
        buffer=None,
        pen_type: int = PEN_RGB565,
        extra_pins=None,
        width: int = None,
        height: int = None,
    ):
        self.display_type = display
        self._rotate = rotate
        self._pen_type = pen_type

        # Get dimensions - use explicit width/height if provided
        if width is not None and height is not None:
            size = (width, height)
        else:
            size = _DISPLAY_SIZES.get(display, (320, 240))

        if rotate in (90, 270):
            self._width, self._height = size[1], size[0]
        else:
            self._width, self._height = size

        # Initialize framebuffer (RGB888 internally for simplicity)
        self._buffer = [[0] * self._width for _ in range(self._height)]
        self._current_pen = 0xFFFFFF  # White default
        self._clip = (0, 0, self._width, self._height)

        # Font settings
        self._font_name = "bitmap8"
        self._font: Optional[BitmapFont] = get_font("bitmap8")
        self._thickness = 1

        # Sprite support
        self._spritesheet = None
        self._spritesheet_width = 0

        # Notify emulator of our existence
        state = get_state()
        state["picographics"] = self

        # Trace logging
        if state.get("trace"):
            print(f"[PicoGraphics] Created display type {display}, size {self._width}x{self._height}")

    @property
    def WIDTH(self) -> int:
        return self._width

    @property
    def HEIGHT(self) -> int:
        return self._height

    def get_bounds(self) -> Tuple[int, int]:
        """Return (width, height) of display."""
        return (self._width, self._height)

    # Pen management
    def set_pen(self, pen: int):
        """Set current drawing pen (color index or RGB value)."""
        self._current_pen = pen

    def create_pen(self, r: int, g: int, b: int) -> int:
        """Create a pen from RGB values (0-255)."""
        return (r << 16) | (g << 8) | b

    def create_pen_hsv(self, h: float, s: float, v: float) -> int:
        """Create a pen from HSV values (0-1)."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return self.create_pen(int(r * 255), int(g * 255), int(b * 255))

    def set_thickness(self, thickness: int):
        """Set line thickness."""
        self._thickness = max(1, thickness)

    # Clipping
    def set_clip(self, x: int, y: int, w: int, h: int):
        """Set clipping rectangle."""
        self._clip = (
            max(0, x),
            max(0, y),
            min(self._width, x + w),
            min(self._height, y + h)
        )

    def remove_clip(self):
        """Remove clipping rectangle."""
        self._clip = (0, 0, self._width, self._height)

    # Drawing primitives
    def clear(self):
        """Fill display with current pen color."""
        for y in range(self._height):
            for x in range(self._width):
                self._buffer[y][x] = self._current_pen

    def pixel(self, x: int, y: int):
        """Draw a single pixel."""
        if self._in_clip(x, y):
            self._buffer[y][x] = self._current_pen

    def pixel_span(self, x: int, y: int, length: int):
        """Draw a horizontal span of pixels."""
        for i in range(length):
            self.pixel(x + i, y)

    def line(self, x1: int, y1: int, x2: int, y2: int, thickness: int = None):
        """Draw a line."""
        if thickness is None:
            thickness = self._thickness
        # Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if thickness == 1:
                self.pixel(x1, y1)
            else:
                self.circle(x1, y1, thickness // 2)

            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def rectangle(self, x: int, y: int, w: int, h: int):
        """Draw a filled rectangle."""
        for py in range(y, y + h):
            for px in range(x, x + w):
                self.pixel(px, py)

    def circle(self, cx: int, cy: int, r: int):
        """Draw a filled circle."""
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                    self.pixel(x, y)

    def triangle(self, x1: int, y1: int, x2: int, y2: int, x3: int, y3: int):
        """Draw a filled triangle."""
        # Simple scanline fill
        min_y = min(y1, y2, y3)
        max_y = max(y1, y2, y3)

        for y in range(min_y, max_y + 1):
            intersects = []
            edges = [(x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x1, y1)]

            for ex1, ey1, ex2, ey2 in edges:
                if ey1 == ey2:
                    continue
                if min(ey1, ey2) <= y < max(ey1, ey2):
                    x = ex1 + (y - ey1) * (ex2 - ex1) / (ey2 - ey1)
                    intersects.append(int(x))

            intersects.sort()
            for i in range(0, len(intersects) - 1, 2):
                for x in range(intersects[i], intersects[i + 1] + 1):
                    self.pixel(x, y)

    def polygon(self, points: List[Tuple[int, int]]):
        """Draw a filled polygon."""
        if len(points) < 3:
            return

        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        for y in range(min_y, max_y + 1):
            intersects = []
            n = len(points)

            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]

                if y1 == y2:
                    continue
                if min(y1, y2) <= y < max(y1, y2):
                    x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                    intersects.append(int(x))

            intersects.sort()
            for i in range(0, len(intersects) - 1, 2):
                for x in range(intersects[i], intersects[i + 1] + 1):
                    self.pixel(x, y)

    # Text rendering
    def set_font(self, font: str):
        """Set current font."""
        self._font_name = font
        self._font = get_font(font)
        if self._font is None:
            self._font = get_font("bitmap8")

    def text(
        self,
        text: str,
        x: int,
        y: int,
        wordwrap: int = -1,
        scale: float = 1.0,
        angle: int = 0,
        spacing: int = 1,
        fixed_width: bool = False,
    ) -> int:
        """Draw text and return width."""
        if not self._font:
            return 0

        scale = int(scale) if scale >= 1 else 1
        char_height = self._font.height * scale

        cx = x
        for char in text:
            if char == '\n':
                cx = x
                y += char_height + spacing
                continue

            # Get character data from font
            columns, char_width = self._font.get_char_data(char)

            if wordwrap > 0 and (cx - x) + (char_width * scale) > wordwrap:
                cx = x
                y += char_height + spacing

            # Draw the character
            self._draw_char_bitmap(columns, char_width, cx, y, scale)
            cx += (char_width + spacing) * scale

        return cx - x

    def _draw_char_bitmap(self, columns: List[int], width: int, x: int, y: int, scale: int):
        """Draw a character from bitmap data."""
        if not self._font:
            return

        height = self._font.height

        for col_idx in range(width):
            if col_idx >= len(columns):
                break

            col_byte = columns[col_idx]

            for row in range(height):
                # Check if this bit is set (LSB = top row)
                if col_byte & (1 << row):
                    # Draw scaled pixel
                    for sy in range(scale):
                        for sx in range(scale):
                            px = x + col_idx * scale + sx
                            py = y + row * scale + sy
                            self.pixel(px, py)

    def character(self, char: int, x: int, y: int, scale: float = 1.0):
        """Draw a single character by ASCII code."""
        if not self._font:
            return

        columns, width = self._font.get_char_data(chr(char))
        self._draw_char_bitmap(columns, width, x, y, int(scale) if scale >= 1 else 1)

    def measure_text(self, text: str, scale: float = 1.0, spacing: int = 1) -> int:
        """Measure text width without drawing."""
        if not self._font:
            return 0

        scale = int(scale) if scale >= 1 else 1
        return self._font.measure_text(text, spacing) * scale

    # Display update
    def update(self):
        """Push framebuffer to display."""
        state = get_state()

        if state.get("trace"):
            print(f"[PicoGraphics] update() called, frame {state.get('frame_count', 0)}")

        # Notify display renderer
        display = get_display()
        if display:
            display.render(self._buffer)

        state["frame_count"] = state.get("frame_count", 0) + 1

    def partial_update(self, x: int, y: int, w: int, h: int):
        """Partial display update (for e-ink)."""
        self.update()

    # Backlight control
    def set_backlight(self, brightness: float):
        """Set backlight brightness (0.0 to 1.0)."""
        state = get_state()
        if state.get("trace"):
            print(f"[PicoGraphics] set_backlight({brightness})")

    # Layer support (for devices with multiple layers)
    def set_layer(self, layer: int):
        """Set current drawing layer."""
        self._current_layer = layer
        state = get_state()
        if state.get("trace"):
            print(f"[PicoGraphics] set_layer({layer})")

    # Pen management
    def reset_pen(self, pen: int):
        """Reset a pen to its default color."""
        # In the emulator, pens are RGB values so this is a no-op
        pass

    def update_pen(self, pen: int, r: int, g: int, b: int):
        """Update a pen's color."""
        # Pens are stored as RGB values directly
        pass

    # Sprite support
    def load_spritesheet(self, filename: str):
        """Load a spritesheet from file (8x8 sprite grid)."""
        state = get_state()
        if state.get("trace"):
            print(f"[PicoGraphics] load_spritesheet({filename})")
        self._spritesheet = None
        self._spritesheet_width = 0
        try:
            from PIL import Image
            img = Image.open(filename).convert("RGB")
            self._spritesheet = img
            self._spritesheet_width = img.width // 8
            if state.get("trace"):
                print(f"[PicoGraphics] Loaded spritesheet {img.width}x{img.height}, "
                      f"{self._spritesheet_width} cols")
        except Exception as e:
            if state.get("trace"):
                print(f"[PicoGraphics] Failed to load spritesheet: {e}")

    def sprite(self, index: int, x: int, y: int, *args):
        """Draw an 8x8 sprite from the loaded spritesheet."""
        if not self._spritesheet:
            return
        cols = self._spritesheet_width or 1
        sx = (index % cols) * 8
        sy = (index // cols) * 8
        pixels = self._spritesheet.load()
        for dy in range(8):
            for dx in range(8):
                try:
                    r, g, b = pixels[sx + dx, sy + dy]
                except (IndexError, ValueError):
                    continue
                # Treat black (0,0,0) as transparent
                if r == 0 and g == 0 and b == 0:
                    continue
                old_pen = self._current_pen
                self._current_pen = (r << 16) | (g << 8) | b
                self.pixel(x + dx, y + dy)
                self._current_pen = old_pen

    # Helper methods
    def _in_clip(self, x: int, y: int) -> bool:
        """Check if point is within clip region."""
        return (
            self._clip[0] <= x < self._clip[2] and
            self._clip[1] <= y < self._clip[3]
        )

    def get_buffer(self) -> List[List[int]]:
        """Get raw framebuffer (for testing/emulator use)."""
        return self._buffer


# Convenience function
def get_buffer(graphics: PicoGraphics):
    """Get the raw buffer from a PicoGraphics instance."""
    return graphics.get_buffer()
