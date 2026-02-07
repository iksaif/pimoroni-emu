"""Mock for InkyUC8159 (7-color Inky Impression) displays."""

from typing import Tuple, List, Any
from emulator.mocks.inky.inky import Inky

try:
    from PIL import Image
except ImportError:
    Image = None


# Color constants for 7-color display
BLACK = 0
WHITE = 1
GREEN = 2
BLUE = 3
RED = 4
YELLOW = 5
ORANGE = 6
CLEAN = 7

# Resolution options
RESOLUTION_5_7 = (600, 448)
RESOLUTION_4 = (640, 400)


class InkyUC8159(Inky):
    """7-color Inky Impression display (UC8159 driver).

    Supports Inky Impression 4.0", 5.7", and 7.3" displays.
    """

    # Color constants
    BLACK = BLACK
    WHITE = WHITE
    GREEN = GREEN
    BLUE = BLUE
    RED = RED
    YELLOW = YELLOW
    ORANGE = ORANGE
    CLEAN = CLEAN

    # Default to 5.7" resolution
    WIDTH = 600
    HEIGHT = 448

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
        """Initialize 7-color Inky Impression.

        Args:
            resolution: Display resolution, default (600, 448) for 5.7"
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
            colour="multi",  # 7-color mode
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
        """Get the 7-color palette for ACeP displays."""
        return [
            (0, 0, 0),        # 0 = Black
            (255, 255, 255),  # 1 = White
            (0, 128, 0),      # 2 = Green
            (0, 0, 255),      # 3 = Blue
            (255, 0, 0),      # 4 = Red
            (255, 255, 0),    # 5 = Yellow
            (255, 128, 0),    # 6 = Orange
        ]

    def set_image(self, image, saturation: float = 0.5):
        """Copy an image to the buffer with 7-color quantization.

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

        # Quantize to 7-color palette
        image = self._convert_to_palette(image, saturation)

        # Copy to buffer
        pixels = image.load()
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self._buffer[y][x] = pixels[x, y]
