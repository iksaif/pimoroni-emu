"""Mock implementation of RGB encoder wheel breakout."""

from emulator.mocks.base import I2CSensorMock

NUM_LEDS = 24
NUM_BUTTONS = 5
NUM_GPIOS = 3

UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3
CENTRE = 4


class BreakoutEncoderWheel(I2CSensorMock):
    """RGB encoder wheel with 24 LEDs and 5 buttons."""

    _component_name = "EncoderWheel"
    _default_address = 0x13

    def __init__(self, i2c, address=0x13, interrupt=None):
        super().__init__(i2c, address)
        self._count = 0
        self._leds = [(0, 0, 0)] * NUM_LEDS
        self._pressed = [False] * NUM_BUTTONS

    def pressed(self, button):
        if 0 <= button < NUM_BUTTONS:
            return self._pressed[button]
        return False

    def count(self):
        return self._count

    def delta(self):
        return 0

    def step(self):
        return 0

    def set_rgb(self, index, r, g, b):
        if 0 <= index < NUM_LEDS:
            self._leds[index] = (r, g, b)

    def set_hsv(self, index, h, s=1.0, v=1.0):
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_rgb(index, int(r * 255), int(g * 255), int(b * 255))

    def clear(self):
        self._leds = [(0, 0, 0)] * NUM_LEDS

    def show(self):
        pass

    def gpio_pin_mode(self, gpio, mode): pass
    def gpio_pin_value(self, gpio, value=None):
        return 0
