"""Mock implementation of VL53L5CX 8x8 multizone ToF sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutVL53L5CX(I2CSensorMock):
    """VL53L5CX 8x8 multizone Time-of-Flight ranging sensor."""

    _component_name = "VL53L5CX"
    _default_address = 0x29

    def __init__(self, i2c, address=0x29, firmware=None):
        super().__init__(i2c, address)
        self._resolution = 4  # 4x4 or 8x8
        self._ranging = False

    def start_ranging(self):
        self._ranging = True

    def stop_ranging(self):
        self._ranging = False

    def set_resolution(self, resolution):
        self._resolution = resolution

    def data_ready(self):
        return self._ranging

    def get_data(self):
        """Returns distance data. Object with .distance_mm list."""
        n = self._resolution * self._resolution
        return type('Data', (), {
            'distance_mm': [500] * n,
            'reflectance': [50] * n,
            'target_status': [5] * n,
        })()

    def set_ranging_frequency_hz(self, freq): pass
    def set_integration_time_ms(self, ms): pass
    def set_sharpener_percent(self, percent): pass
    def set_ranging_mode(self, mode): pass
    def set_power_mode(self, mode): pass
