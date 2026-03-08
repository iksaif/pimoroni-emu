"""Mock for Spectra 6-color displays (E673, E640, EL133UF1).

Spectra 6 panels have 6 colors with a different index mapping from AC073TC1A/UC8159:
  BLACK=0, WHITE=1, YELLOW=2, RED=3, BLUE=5, GREEN=6
Note: index 4 is unused (skipped in the hardware remap).
"""

from typing import Any, List, Tuple

from emulator.mocks.inky.inky import Inky

try:
    from PIL import Image
except ImportError:
    Image = None


# Color constants for Spectra 6 displays (matches upstream E673/E640/EL133UF1)
BLACK = 0
WHITE = 1
YELLOW = 2
RED = 3
BLUE = 5
GREEN = 6
CLEAN = 7


class InkySpectra6(Inky):
    """6-color Spectra display (E673 / E640 / EL133UF1).

    Supports 6 colors: black, white, yellow, red, blue, green (no orange).
    Color indices differ from AC073TC1A/UC8159.
    """

    # Color constants
    BLACK = BLACK
    WHITE = WHITE
    YELLOW = YELLOW
    RED = RED
    BLUE = BLUE
    GREEN = GREEN
    CLEAN = CLEAN

    # Default to 7.3" E673 resolution
    WIDTH = 800
    HEIGHT = 480

    def __init__(
        self,
        resolution: Tuple[int, int] = None,
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
        """Initialize Spectra 6-color display.

        Args:
            resolution: Display resolution, default (800, 480)
            cs_pin: SPI chip select pin
            dc_pin: Data/command pin
            reset_pin: Reset pin
            busy_pin: Busy pin
            h_flip: Horizontal flip
            v_flip: Vertical flip
        """
        if resolution:
            self.WIDTH, self.HEIGHT = resolution

        super().__init__(
            resolution=(self.WIDTH, self.HEIGHT),
            colour="multi",
            cs_pin=cs_pin,
            dc_pin=dc_pin,
            reset_pin=reset_pin,
            busy_pin=busy_pin,
            h_flip=h_flip,
            v_flip=v_flip,
            spi_bus=spi_bus,
            i2c_bus=i2c_bus,
            gpio=gpio,
        )

    def _get_palette(self) -> List[Tuple[int, int, int]]:
        """Get the 6-color Spectra palette.

        Note: index 4 is unused in Spectra 6 hardware but included as a
        gray fallback so palette indexing works for any value 0-6.
        """
        return [
            (0, 0, 0),        # 0 = Black
            (255, 255, 255),  # 1 = White
            (255, 255, 0),    # 2 = Yellow
            (255, 0, 0),      # 3 = Red
            (128, 128, 128),  # 4 = (unused, gray fallback)
            (0, 0, 255),      # 5 = Blue
            (0, 128, 0),      # 6 = Green
        ]

    def set_image(self, image, saturation: float = 0.5):
        """Copy an image to the buffer with 6-color quantization.

        Args:
            image: PIL Image
            saturation: Color saturation (0.0 - 1.0)
        """
        if Image is None:
            raise ImportError("PIL/Pillow is required for set_image()")

        # Convert to PIL Image if needed
        if not isinstance(image, Image.Image):
            image = Image.fromarray(image)

        # Resize to display dimensions
        image = image.resize((self.WIDTH, self.HEIGHT))

        # Convert to RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Apply saturation
        if saturation != 1.0:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(saturation)

        # Quantize to 6-color palette
        image = self._convert_to_palette(image, saturation)

        # Copy to buffer
        pixels = image.load()
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self._buffer[y][x] = pixels[x, y]
