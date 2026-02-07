"""Mock implementation of BME68X temperature/humidity/pressure/gas sensor."""

from emulator.mocks.base import I2CSensorMock

# Filter coefficients
FILTER_COEFF_OFF = 0
FILTER_COEFF_1 = 1
FILTER_COEFF_3 = 2
FILTER_COEFF_7 = 3
FILTER_COEFF_15 = 4
FILTER_COEFF_31 = 5
FILTER_COEFF_63 = 6
FILTER_COEFF_127 = 7

# Oversampling
NO_OVERSAMPLING = 0
OVERSAMPLING_1X = 1
OVERSAMPLING_2X = 2
OVERSAMPLING_4X = 3
OVERSAMPLING_8X = 4
OVERSAMPLING_16X = 5

# Modes
SLEEP_MODE = 0
FORCED_MODE = 1
NORMAL_MODE = 2

# Standby times
STANDBY_TIME_0_59_MS = 0
STANDBY_TIME_62_5_MS = 1
STANDBY_TIME_125_MS = 2
STANDBY_TIME_250_MS = 3
STANDBY_TIME_500_MS = 4
STANDBY_TIME_1000_MS = 5
STANDBY_TIME_10_MS = 6
STANDBY_TIME_20_MS = 7

# Status
STATUS_HEATER_STABLE = 0x10


class BreakoutBME68X(I2CSensorMock):
    """BME68X environmental sensor with gas resistance."""

    _component_name = "BME68X"
    _default_address = 0x76
    I2C_ADDRESS_DEFAULT = 0x76
    I2C_ADDRESS_ALT = 0x77

    def __init__(self, i2c, address=0x76):
        super().__init__(i2c, address)
        self._temperature = 22.5
        self._pressure = 1013.25
        self._humidity = 45.0
        self._gas_resistance = 50000.0
        self._register("bme68x")

    def read(self, heater_temp=300, heater_duration=100):
        """Read sensor. Returns (temp, pressure, humidity, gas, status, gas_index, meas_index)."""
        return (self._temperature, self._pressure, self._humidity,
                self._gas_resistance, STATUS_HEATER_STABLE, 0, 0)

    def configure(self, *args, **kwargs):
        pass

    def _set_values(self, temp=None, pressure=None, humidity=None, gas=None):
        if temp is not None:
            self._temperature = temp
        if pressure is not None:
            self._pressure = pressure
        if humidity is not None:
            self._humidity = humidity
        if gas is not None:
            self._gas_resistance = gas
