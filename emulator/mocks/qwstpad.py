"""Mock implementation of QwSTPad controller (I2C gamepad)."""

from emulator.mocks.base import I2CSensorMock

# I2C addresses
ADDRESSES = [0x21, 0x22, 0x23, 0x24]

# Button constants
BUTTON_A = 0x01
BUTTON_B = 0x02
BUTTON_X = 0x04
BUTTON_Y = 0x08
BUTTON_PLUS = 0x10
BUTTON_MINUS = 0x20
BUTTON_U = 0x40
BUTTON_D = 0x80
BUTTON_L = 0x100
BUTTON_R = 0x200

# Button name to constant mapping
BUTTON_MAP = {
    "A": BUTTON_A,
    "B": BUTTON_B,
    "X": BUTTON_X,
    "Y": BUTTON_Y,
    "+": BUTTON_PLUS,
    "-": BUTTON_MINUS,
    "U": BUTTON_U,
    "D": BUTTON_D,
    "L": BUTTON_L,
    "R": BUTTON_R,
}


class ButtonState(dict):
    """Dictionary-like object for button state access."""

    def __init__(self, buttons_bitmask):
        super().__init__()
        self._bitmask = buttons_bitmask
        # Populate dict with button states
        for name, mask in BUTTON_MAP.items():
            self[name] = bool(buttons_bitmask & mask)

    def __int__(self):
        """Allow using as integer bitmask."""
        return self._bitmask


class QwSTPad(I2CSensorMock):
    """QwSTPad I2C gamepad controller."""

    _component_name = "QwSTPad"
    _default_address = ADDRESSES[0]

    def __init__(self, i2c, address=ADDRESSES[0]):
        super().__init__(i2c, address)
        self._buttons = 0
        # Register with emulator state for input panel (if needed)
        self._register("qwstpad")

    def read_buttons(self):
        """Read current button state as dictionary-like object.

        Returns a ButtonState that supports both dict access (button["L"])
        and can be converted to int for bitmask operations.
        """
        return ButtonState(self._buttons)

    @property
    def button_a(self):
        return bool(self._buttons & BUTTON_A)

    @property
    def button_b(self):
        return bool(self._buttons & BUTTON_B)

    @property
    def button_x(self):
        return bool(self._buttons & BUTTON_X)

    @property
    def button_y(self):
        return bool(self._buttons & BUTTON_Y)

    @property
    def button_plus(self):
        return bool(self._buttons & BUTTON_PLUS)

    @property
    def button_minus(self):
        return bool(self._buttons & BUTTON_MINUS)

    @property
    def button_u(self):
        return bool(self._buttons & BUTTON_U)

    @property
    def button_d(self):
        return bool(self._buttons & BUTTON_D)

    @property
    def button_l(self):
        return bool(self._buttons & BUTTON_L)

    @property
    def button_r(self):
        return bool(self._buttons & BUTTON_R)

    def set_led(self, led, state):
        """Set LED state."""
        self._trace(f"LED {led} = {state}")

    def set_leds(self, leds):
        """Set all LEDs from a bitmask."""
        self._trace(f"set_leds(0b{leds:04b})")

    def clear_leds(self):
        """Clear all LEDs."""
        self._trace("Cleared all LEDs")

    def address_code(self):
        """Get address code (0-3) based on I2C address."""
        try:
            return ADDRESSES.index(self._address)
        except ValueError:
            return 0

    def _set_buttons(self, buttons):
        """Set mock button state for testing."""
        self._buttons = buttons
