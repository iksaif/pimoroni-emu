"""Mock implementation of AS7262 6-channel spectral sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutAS7262(I2CSensorMock):
    """AS7262 6-channel visible light spectral sensor."""

    _component_name = "AS7262"
    _default_address = 0x49

    def __init__(self, i2c, address=0x49):
        super().__init__(i2c, address)

    def read(self):
        """Read 6 spectral channels (violet, blue, green, yellow, orange, red)."""
        return (10.0, 20.0, 30.0, 25.0, 15.0, 10.0)

    def set_gain(self, gain): pass
    def set_measurement_mode(self, mode): pass
    def set_indicator_current(self, current): pass
    def set_illumination_current(self, current): pass
    def set_integration_time(self, time): pass
    def set_leds(self, on): pass

    def temperature(self):
        return 25
