"""Mock implementation of BMP280 temperature/pressure sensor."""

from emulator.mocks.base import I2CSensorMock

FILTER_COEFF_OFF = 0
FILTER_COEFF_2 = 1
FILTER_COEFF_4 = 2
FILTER_COEFF_8 = 3
FILTER_COEFF_16 = 4

NO_OVERSAMPLING = 0
OVERSAMPLING_1X = 1
OVERSAMPLING_2X = 2
OVERSAMPLING_4X = 3
OVERSAMPLING_8X = 4
OVERSAMPLING_16X = 5

SLEEP_MODE = 0
FORCED_MODE = 1
NORMAL_MODE = 3

STANDBY_TIME_0_5_MS = 0
STANDBY_TIME_62_5_MS = 1
STANDBY_TIME_125_MS = 2
STANDBY_TIME_250_MS = 3
STANDBY_TIME_500_MS = 4
STANDBY_TIME_1000_MS = 5
STANDBY_TIME_2000_MS = 6
STANDBY_TIME_4000_MS = 7

BMP280_DEFAULT_I2C_ADDRESS = 0x76


class BreakoutBMP280(I2CSensorMock):
    """BMP280 temperature and pressure sensor."""

    _component_name = "BMP280"
    _default_address = 0x76

    def __init__(self, i2c, address=0x76):
        super().__init__(i2c, address)
        self._temperature = 22.5
        self._pressure = 1013.25
        self._register("bmp280")

    def read(self):
        """Read sensor. Returns (temperature, pressure)."""
        return (self._temperature, self._pressure)

    def configure(self, *args, **kwargs):
        pass

    def _set_values(self, temp=None, pressure=None):
        if temp is not None:
            self._temperature = temp
        if pressure is not None:
            self._pressure = pressure
