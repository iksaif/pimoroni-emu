"""Mock implementation of AS7343 14-channel spectral sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutAS7343(I2CSensorMock):
    """AS7343 14-channel spectral sensor."""

    _component_name = "AS7343"
    _default_address = 0x39

    def __init__(self, i2c, address=0x39):
        super().__init__(i2c, address)

    def read(self):
        """Read all 14 spectral channels. Returns tuple of 14 floats."""
        return tuple([100.0] * 14)

    def set_channels(self, channels): pass
    def set_gain(self, gain): pass
    def set_integration_time(self, time): pass
    def set_measurement_mode(self, mode): pass
    def set_illumination_current(self, current): pass
    def set_illumination_led(self, on): pass
