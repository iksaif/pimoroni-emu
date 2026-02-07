"""Mock implementation of 5x7 LED dot matrix breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutDotMatrix(I2CSensorMock):
    """IS31FL3730 5x7 LED dot matrix display."""

    _component_name = "DotMatrix"
    _default_address = 0x61

    WIDTH = 5
    HEIGHT = 7

    def __init__(self, i2c, address=0x61):
        super().__init__(i2c, address)
        self._buffer = [[0] * self.WIDTH for _ in range(self.HEIGHT)]

    def set_pixel(self, x, y, on=True):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            self._buffer[y][x] = 1 if on else 0

    def set_image(self, image, offset_x=0, offset_y=0, wrap=False):
        pass

    def set_decimal(self, left=False, right=False):
        pass

    def clear(self):
        self._buffer = [[0] * self.WIDTH for _ in range(self.HEIGHT)]

    def show(self):
        pass

    def set_brightness(self, brightness, update=True):
        pass
