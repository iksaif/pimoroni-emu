"""Mock implementation of BH1745 colour sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutBH1745(I2CSensorMock):
    """BH1745 RGBC colour sensor."""

    _component_name = "BH1745"
    _default_address = 0x38

    def __init__(self, i2c, address=0x38):
        super().__init__(i2c, address)
        self._r = 100
        self._g = 100
        self._b = 100
        self._c = 300  # Clear channel

    def read(self):
        """Read colour channels. Returns (r, g, b, c)."""
        return (self._r, self._g, self._b, self._c)

    def leds(self, on=True):
        pass

    def set_measurement_time_ms(self, ms):
        pass

    def set_threshold_high(self, val): pass
    def set_threshold_low(self, val): pass
