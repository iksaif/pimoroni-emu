"""Mock implementation of BME280 temperature/humidity/pressure sensor."""

from emulator.mocks.base import I2CSensorMock


class BreakoutBME280(I2CSensorMock):
    """BME280 environmental sensor."""

    _component_name = "BME280"
    _default_address = 0x76

    def __init__(self, i2c, address=0x76):
        super().__init__(i2c, address)
        # Default mock values
        self._temperature = 22.5
        self._pressure = 1013.25
        self._humidity = 45.0
        # Register with emulator state for sensor panel
        self._register("bme280")

    def read(self):
        """Read sensor values. Returns (temperature, pressure, humidity)."""
        return (self._temperature, self._pressure, self._humidity)

    def configure(self, *args, **kwargs):
        """Configure sensor (no-op in mock)."""
        pass

    def _set_values(self, temp=None, pressure=None, humidity=None):
        """Set mock sensor values for testing."""
        if temp is not None:
            self._temperature = temp
        if pressure is not None:
            self._pressure = pressure
        if humidity is not None:
            self._humidity = humidity
