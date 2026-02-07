"""Mock implementation of ICP-10125 pressure/temperature sensor breakout."""

from emulator.mocks.base import I2CSensorMock

NORMAL = 0
LOW_POWER = 1
LOW_NOISE = 2
ULTRA_LOW_NOISE = 3


class BreakoutICP10125(I2CSensorMock):
    """ICP-10125 high-accuracy pressure and temperature sensor."""

    _component_name = "ICP10125"
    _default_address = 0x63

    def __init__(self, i2c, address=0x63):
        super().__init__(i2c, address)
        self._temperature = 22.5
        self._pressure = 1013.25

    def measure(self, mode=NORMAL):
        """Read sensor. Returns (temperature, pressure, status)."""
        return (self._temperature, self._pressure, 0)

    def soft_reset(self):
        pass
