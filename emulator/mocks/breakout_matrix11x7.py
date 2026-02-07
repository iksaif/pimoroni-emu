"""Mock implementation of 11x7 LED matrix breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutMatrix11x7(I2CSensorMock):
    """IS31FL3731 11x7 LED matrix."""

    _component_name = "Matrix11x7"
    _default_address = 0x75

    WIDTH = 11
    HEIGHT = 7

    def __init__(self, i2c, address=0x75):
        super().__init__(i2c, address)
        self._buffer = [[0] * self.WIDTH for _ in range(self.HEIGHT)]

    def set_pixel(self, x, y, val):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            self._buffer[y][x] = val

    def clear(self):
        self._buffer = [[0] * self.WIDTH for _ in range(self.HEIGHT)]

    def show(self):
        pass

    def set_brightness(self, brightness):
        pass
