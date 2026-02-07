"""Base Inky class mock for Raspberry Pi e-ink displays."""

from typing import Optional, Tuple, List, Any
from emulator import get_state, get_display

# Try to import PIL for image handling
try:
    from PIL import Image
except ImportError:
    Image = None


# Color constants
WHITE = 0
BLACK = 1
RED = 2
YELLOW = 2
GREEN = 3
BLUE = 4
ORANGE = 5
CLEAN = 6


class Inky:
    """Base class for Inky displays (pHAT, wHAT, etc)."""

    # Default display properties (overridden by subclasses)
    WIDTH = 212
    HEIGHT = 104
    WHITE = WHITE
    BLACK = BLACK
    RED = RED
    YELLOW = YELLOW

    def __init__(
        self,
        resolution: Tuple[int, int] = None,
        colour: str = "black",
        cs_pin: int = 8,
        dc_pin: int = 22,
        reset_pin: int = 27,
        busy_pin: int = 17,
        h_flip: bool = False,
        v_flip: bool = False,
        spi_bus: Any = None,
        i2c_bus: Any = None,
        gpio: Any = None,
    ):
        """Initialize Inky display.

        Args:
            resolution: Display resolution (width, height)
            colour: Color mode ("black", "red", "yellow", "multi")
            cs_pin: SPI chip select pin
            dc_pin: Data/command pin
            reset_pin: Reset pin
            busy_pin: Busy pin
            h_flip: Horizontal flip
            v_flip: Vertical flip
            spi_bus: SPI bus (ignored in emulator)
            i2c_bus: I2C bus (ignored in emulator)
            gpio: GPIO module (ignored in emulator)
        """
        if resolution:
            self.WIDTH, self.HEIGHT = resolution
        self.width = self.WIDTH
        self.height = self.HEIGHT

        self.colour = colour
        self.h_flip = h_flip
        self.v_flip = v_flip

        # Buffer for pixel data
        self._buffer = [[WHITE] * self.WIDTH for _ in range(self.HEIGHT)]

        # Border color
        self._border = WHITE

        # Register with emulator
        state = get_state()
        state["inky"] = self

        if state.get("trace"):
            print(f"[Inky] Created {self.WIDTH}x{self.HEIGHT} display, colour={colour}")

    def setup(self):
        """Set up Inky GPIO and reset display."""
        state = get_state()
        if state.get("trace"):
            print("[Inky] setup() called")

    def set_pixel(self, x: int, y: int, v: int):
        """Set a single pixel on the buffer.

        Args:
            x: X coordinate
            y: Y coordinate
            v: Color value (WHITE, BLACK, RED, etc)
        """
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            self._buffer[y][x] = v

    def set_border(self, colour: int):
        """Set the border colour.

        Args:
            colour: Border color constant
        """
        self._border = colour

    def set_image(self, image, saturation: float = 0.5):
        """Copy an image to the buffer.

        Args:
            image: PIL Image or numpy array
            saturation: Saturation for color conversion
        """
        if Image is None:
            raise ImportError("PIL/Pillow is required for set_image()")

        # Convert to PIL Image if needed
        if not isinstance(image, Image.Image):
            image = Image.fromarray(image)

        # Resize to display dimensions
        image = image.resize((self.WIDTH, self.HEIGHT))

        # Convert to palette
        if image.mode != "P":
            image = self._convert_to_palette(image, saturation)

        # Copy to buffer
        pixels = image.load()
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self._buffer[y][x] = pixels[x, y]

    def _convert_to_palette(self, image, saturation: float):
        """Convert image to display palette."""
        # Convert to RGB first
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Create palette image
        palette_image = Image.new("P", (1, 1))

        # Define palette (depends on display type)
        palette = self._get_palette()
        palette_data = []
        for r, g, b in palette:
            palette_data.extend([r, g, b])
        # Pad to 256 colors
        while len(palette_data) < 768:
            palette_data.extend([0, 0, 0])

        palette_image.putpalette(palette_data)

        # Quantize image to palette
        return image.quantize(palette=palette_image, dither=Image.Dither.FLOYDSTEINBERG)

    def _get_palette(self) -> List[Tuple[int, int, int]]:
        """Get the color palette for this display."""
        if self.colour == "black":
            return [(255, 255, 255), (0, 0, 0)]
        elif self.colour in ("red", "yellow"):
            if self.colour == "red":
                accent = (255, 0, 0)
            else:
                accent = (255, 255, 0)
            return [(255, 255, 255), (0, 0, 0), accent]
        else:
            # 7-color palette
            return [
                (0, 0, 0),        # Black
                (255, 255, 255),  # White
                (0, 128, 0),      # Green
                (0, 0, 255),      # Blue
                (255, 0, 0),      # Red
                (255, 255, 0),    # Yellow
                (255, 128, 0),    # Orange
            ]

    def show(self, busy_wait: bool = True):
        """Show buffer on display.

        Args:
            busy_wait: Wait for display to finish updating
        """
        state = get_state()

        if state.get("trace"):
            print(f"[Inky] show() called, busy_wait={busy_wait}")

        # Apply flipping if needed
        buffer = self._buffer
        if self.h_flip:
            buffer = [row[::-1] for row in buffer]
        if self.v_flip:
            buffer = buffer[::-1]

        # Convert color indices to RGB for display
        palette = self._get_palette()
        rgb_buffer = []
        for row in buffer:
            rgb_row = []
            for color_idx in row:
                if 0 <= color_idx < len(palette):
                    r, g, b = palette[color_idx]
                else:
                    r, g, b = 255, 255, 255
                rgb_row.append((r << 16) | (g << 8) | b)
            rgb_buffer.append(rgb_row)

        # Notify display renderer
        display = get_display()
        if display:
            display.render(rgb_buffer)

        state["frame_count"] = state.get("frame_count", 0) + 1

    def get_buffer(self) -> List[List[int]]:
        """Get raw buffer (for testing/emulator use)."""
        return self._buffer


class InkyMock(Inky):
    """Alias for Inky class for compatibility."""
    pass
