"""Mock implementation of LTR559 light and proximity sensor."""

from emulator.mocks.base import I2CSensorMock


class BreakoutLTR559(I2CSensorMock):
    """LTR559 light and proximity sensor."""

    # Index constants for tuple returned by get_reading()
    LUX = 0
    PROXIMITY = 1

    _component_name = "LTR559"
    _default_address = 0x23

    def __init__(self, i2c=None, address=0x23):
        super().__init__(i2c, address)
        # Default mock values
        self._lux = 100.0
        self._proximity = 0
        # Register with emulator state for sensor panel
        self._register("ltr559")

    def get_lux(self):
        """Get light level in lux."""
        return self._lux

    def get_proximity(self):
        """Get proximity value (0-65535)."""
        return self._proximity

    def get_reading(self):
        """Get both lux and proximity."""
        return (self._lux, self._proximity)

    def _set_values(self, lux=None, proximity=None):
        """Set mock sensor values for testing."""
        if lux is not None:
            self._lux = lux
        if proximity is not None:
            self._proximity = proximity
