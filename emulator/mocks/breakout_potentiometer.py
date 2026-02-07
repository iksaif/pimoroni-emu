"""Mock implementation of potentiometer breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutPotentiometer(I2CSensorMock):
    """Analog potentiometer with I2C ADC."""

    _component_name = "Potentiometer"
    _default_address = 0x0E

    def __init__(self, i2c, address=0x0E):
        super().__init__(i2c, address)
        self._value = 0.5
        self._direction = True  # True = clockwise

    def read(self):
        """Read potentiometer position (0.0 to 1.0)."""
        return self._value

    def set_direction(self, clockwise=True):
        self._direction = clockwise

    def set_brightness(self, brightness):
        pass

    def set_led(self, r, g, b):
        pass
