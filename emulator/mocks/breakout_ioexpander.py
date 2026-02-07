"""Mock implementation of IO Expander breakout."""

from emulator.mocks.base import I2CSensorMock

# Pin modes
PIN_MODE_IO = 0
PIN_MODE_PWM = 1
PIN_MODE_ADC = 2

IN = 0x00
IN_PU = 0x10
OUT = 0x01
PWM = 0x05
ADC = 0x0A

HIGH = 1
LOW = 0


class BreakoutIOExpander(I2CSensorMock):
    """Nuvoton MS51 IO Expander."""

    _component_name = "IOExpander"
    _default_address = 0x18

    def __init__(self, i2c, address=0x18, interrupt=None):
        super().__init__(i2c, address)
        self._pins = {}

    def set_mode(self, pin, mode):
        self._pins[pin] = {"mode": mode, "value": 0}

    def input(self, pin):
        return self._pins.get(pin, {}).get("value", 0)

    def output(self, pin, value):
        if pin in self._pins:
            self._pins[pin]["value"] = value

    def get_adc(self, pin):
        return 0.0

    def set_pwm_period(self, period): pass
    def set_pwm_control(self, divider): pass
    def set_addr(self, addr): pass

    def get_chip_id(self):
        return 0x0E20
