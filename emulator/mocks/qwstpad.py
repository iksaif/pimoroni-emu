"""Mock implementation of QwSTPad controller (I2C gamepad)."""

from collections import OrderedDict
from emulator.mocks.base import I2CSensorMock
from emulator import get_state

# I2C addresses (matching upstream: 0x21, 0x23, 0x25, 0x27)
DEFAULT_ADDRESS = 0x21
ALT_ADDRESS_1 = 0x23
ALT_ADDRESS_2 = 0x25
ALT_ADDRESS_3 = 0x27
ADDRESSES = (DEFAULT_ADDRESS, ALT_ADDRESS_1, ALT_ADDRESS_2, ALT_ADDRESS_3)

NUM_LEDS = 4
NUM_BUTTONS = 10

# Button constants (bitmask values)
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

# Button name to constant mapping (ordered like upstream)
BUTTON_MAP = OrderedDict({
    "A": BUTTON_A,
    "B": BUTTON_B,
    "X": BUTTON_X,
    "Y": BUTTON_Y,
    "U": BUTTON_U,
    "D": BUTTON_D,
    "L": BUTTON_L,
    "R": BUTTON_R,
    "+": BUTTON_PLUS,
    "-": BUTTON_MINUS,
})

# Keyboard key name → QwSTPad button bitmask
KEY_TO_BUTTON = {
    "up": BUTTON_U,
    "down": BUTTON_D,
    "left": BUTTON_L,
    "right": BUTTON_R,
    "z": BUTTON_A,
    "x": BUTTON_B,
    "c": BUTTON_X,
    "v": BUTTON_Y,
    "=": BUTTON_PLUS,
    "-": BUTTON_MINUS,
}

# Button name → keyboard key name (for UI display)
BUTTON_TO_KEY = {
    "A": "z",
    "B": "x",
    "X": "c",
    "Y": "v",
    "U": "up",
    "D": "down",
    "L": "left",
    "R": "right",
    "+": "=",
    "-": "-",
}


class QwSTPad(I2CSensorMock):
    """QwSTPad I2C gamepad controller."""

    _component_name = "QwSTPad"
    _default_address = DEFAULT_ADDRESS

    def __init__(self, i2c, address=DEFAULT_ADDRESS, show_address=True):
        if address not in ADDRESSES:
            raise ValueError("address is not valid. Expected: 0x21, 0x23, 0x25, or 0x27")
        super().__init__(i2c, address)
        self._led_states = 0b0000

        # Register with emulator state for input wiring and UI
        self._register("qwstpad")

        # Initialize button state in emulator
        state = get_state()
        if "qwstpad_buttons" not in state:
            state["qwstpad_buttons"] = 0

        if show_address:
            self.set_leds(self.address_code())

    def read_buttons(self):
        """Read current button state as OrderedDict (matching upstream API).

        Returns an OrderedDict with button names as keys and bool values.
        """
        state = get_state()
        bitmask = state.get("qwstpad_buttons", 0)
        result = OrderedDict()
        for name, mask in BUTTON_MAP.items():
            result[name] = bool(bitmask & mask)
        return result

    @property
    def button_a(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_A)

    @property
    def button_b(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_B)

    @property
    def button_x(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_X)

    @property
    def button_y(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_Y)

    @property
    def button_plus(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_PLUS)

    @property
    def button_minus(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_MINUS)

    @property
    def button_u(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_U)

    @property
    def button_d(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_D)

    @property
    def button_l(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_L)

    @property
    def button_r(self):
        return bool(get_state().get("qwstpad_buttons", 0) & BUTTON_R)

    def set_led(self, led, state):
        """Set LED state (1-indexed, matching upstream)."""
        if led < 1 or led > NUM_LEDS:
            raise ValueError("'led' out of range. Expected 1 to 4")
        if state:
            self._led_states |= (1 << (led - 1))
        else:
            self._led_states &= ~(1 << (led - 1))
        self._trace(f"LED {led} = {state}")

    def set_leds(self, states):
        """Set all LEDs from a bitmask."""
        self._led_states = states & 0b1111
        self._trace(f"set_leds(0b{self._led_states:04b})")

    def clear_leds(self):
        """Clear all LEDs."""
        self._led_states = 0b0000
        self._trace("Cleared all LEDs")

    def address_code(self):
        """Get address code bitmask based on I2C address (matching upstream)."""
        try:
            idx = ADDRESSES.index(self._address)
            return 1 << idx
        except ValueError:
            return 0

    def _set_buttons(self, buttons):
        """Set mock button state for testing."""
        get_state()["qwstpad_buttons"] = buttons
