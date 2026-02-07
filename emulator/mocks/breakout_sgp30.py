"""Mock implementation of SGP30 air quality sensor."""

from emulator.mocks.base import I2CSensorMock


class BreakoutSGP30(I2CSensorMock):
    """SGP30 air quality sensor (eCO2 and TVOC)."""

    _component_name = "SGP30"
    _default_address = 0x58

    def __init__(self, i2c, address=0x58):
        super().__init__(i2c, address)
        self._eco2 = 400
        self._tvoc = 0

    def start_measurement(self, humid_compensate=False):
        pass

    def get_air_quality(self):
        """Returns (eCO2 ppm, TVOC ppb)."""
        return (self._eco2, self._tvoc)

    def get_air_quality_raw(self):
        """Returns raw (H2, Ethanol) signals."""
        return (13000, 17000)

    def soft_reset(self):
        pass

    def get_unique_id(self):
        return 0x123456
