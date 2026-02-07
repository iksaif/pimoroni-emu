"""Mock implementation of the blinky native module for Blinky 2350.

The blinky module provides the display driver for the 39x26 LED matrix display.
"""

from emulator import get_state


# Display dimensions (39x26 = 1014 LED positions, 872 actual LEDs)
WIDTH = 39
HEIGHT = 26


class Blinky:
    """Blinky LED matrix display driver."""

    WIDTH = WIDTH
    HEIGHT = HEIGHT

    def __init__(self):
        self._brightness = 1.0
        # Framebuffer: grayscale values 0-255 for each LED
        self._buffer = bytearray(WIDTH * HEIGHT)

        # Register with emulator state
        state = get_state()
        state["blinky_display"] = self

        if state.get("trace"):
            print(f"[blinky] Initialized {WIDTH}x{HEIGHT} display")

    def __buffer__(self, flags):
        """Support memoryview() - returns the framebuffer."""
        return self._buffer

    def set_brightness(self, value: float):
        """Set display brightness (0.0-1.0)."""
        self._brightness = max(0.0, min(1.0, value))
        if get_state().get("trace"):
            print(f"[blinky] Brightness: {self._brightness}")

    def update(self, picographics_display=None):
        """Push framebuffer to display.

        Args:
            picographics_display: Optional PicoGraphics display to render from.
                                  If provided, copies its buffer to the LED matrix.
        """
        state = get_state()
        display = state.get("display")

        # If a PicoGraphics display is provided, copy its buffer
        if picographics_display is not None and hasattr(picographics_display, '_buffer'):
            pg_buffer = picographics_display._buffer
            for y in range(min(HEIGHT, len(pg_buffer))):
                for x in range(min(WIDTH, len(pg_buffer[y]))):
                    color = pg_buffer[y][x]
                    # Convert RGB to grayscale
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                    self._buffer[y * WIDTH + x] = gray

        if display:
            # Convert 1D buffer to 2D for the display renderer
            buffer_2d = []
            for y in range(HEIGHT):
                row = []
                for x in range(WIDTH):
                    # Get grayscale value and apply brightness
                    gray = self._buffer[y * WIDTH + x]
                    gray = int(gray * self._brightness)
                    # Pack as RGB (white LEDs)
                    row.append((gray << 16) | (gray << 8) | gray)
                buffer_2d.append(row)
            display.render(buffer_2d)

        # Track frame count in emulator state
        state["frame_count"] = state.get("frame_count", 0) + 1

        if state.get("trace"):
            print(f"[blinky] Display updated, frame {state['frame_count']}")

    def clear(self):
        """Clear the display buffer."""
        for i in range(len(self._buffer)):
            self._buffer[i] = 0
