"""Mock implementation of trackball breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutTrackball(I2CSensorMock):
    """I2C trackball with RGBW LED."""

    _component_name = "Trackball"
    _default_address = 0x0A

    def __init__(self, i2c, address=0x0A, interrupt=None):
        super().__init__(i2c, address)

    def read(self):
        """Read trackball. Returns (left, right, up, down, click)."""
        return (0, 0, 0, 0, 0)

    def set_rgbw(self, r, g, b, w):
        pass

    def set_red(self, val): pass
    def set_green(self, val): pass
    def set_blue(self, val): pass
    def set_white(self, val): pass
