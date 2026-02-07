"""Mock implementation of rotary encoder breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutEncoder(I2CSensorMock):
    """I2C rotary encoder with RGB LED."""

    _component_name = "Encoder"
    _default_address = 0x0F

    def __init__(self, i2c, address=0x0F, interrupt=None):
        super().__init__(i2c, address)
        self._count = 0
        self._pressed = False

    def get_count(self):
        return self._count

    def set_count(self, count):
        self._count = count

    def get_step(self):
        """Get step since last call (-1, 0, or 1)."""
        return 0

    def pressed(self):
        return self._pressed

    def clear_interrupt(self):
        pass

    def set_led(self, r, g, b):
        pass

    def set_brightness(self, brightness):
        pass
