"""Mock implementation of 5x5 RGB LED matrix breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutRGBMatrix5x5(I2CSensorMock):
    """IS31FL3731 5x5 RGB LED matrix."""

    _component_name = "RGBMatrix5x5"
    _default_address = 0x74

    WIDTH = 5
    HEIGHT = 5

    def __init__(self, i2c, address=0x74):
        super().__init__(i2c, address)
        self._pixels = [[(0, 0, 0)] * self.WIDTH for _ in range(self.HEIGHT)]

    def set_pixel(self, x, y, r, g, b):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            self._pixels[y][x] = (r, g, b)

    def clear(self):
        self._pixels = [[(0, 0, 0)] * self.WIDTH for _ in range(self.HEIGHT)]

    def show(self):
        pass

    def set_brightness(self, brightness):
        pass
