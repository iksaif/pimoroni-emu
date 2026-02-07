"""Mock implementation of Tufty 2350 device module."""

from emulator import get_state
from emulator.mocks.picographics import PicoGraphics, DISPLAY_TUFTY_2350, PEN_RGB565


# Button pin definitions (matching real hardware)
BUTTON_A = 7
BUTTON_B = 8
BUTTON_C = 9
BUTTON_UP = 22
BUTTON_DOWN = 6
BUTTON_BOOT = 23

# LED pin
LED = 25

# Light sensor pin
LIGHT_SENSE = 26

# Display backlight pin
BACKLIGHT = 2


class Tufty2350:
    """Tufty 2350 device controller."""

    def __init__(self):
        # Create display
        self.display = PicoGraphics(
            display=DISPLAY_TUFTY_2350,
            pen_type=PEN_RGB565,
        )

        # Button state
        self._buttons = {
            BUTTON_A: False,
            BUTTON_B: False,
            BUTTON_C: False,
            BUTTON_UP: False,
            BUTTON_DOWN: False,
            BUTTON_BOOT: False,
        }

        # Light sensor value (0-65535)
        self._light_value = 32768

        # Backlight
        self._backlight = 1.0

        # Register with emulator
        state = get_state()
        state["tufty2350"] = self

        if state.get("trace"):
            print("[Tufty2350] Initialized")

    def set_backlight(self, brightness: float):
        """Set display backlight (0.0 to 1.0)."""
        self._backlight = max(0.0, min(1.0, brightness))
        self.display.set_backlight(self._backlight)

    def button(self, pin: int) -> bool:
        """Read button state."""
        return self._buttons.get(pin, False)

    def _set_button(self, pin: int, pressed: bool):
        """Set button state (called by emulator)."""
        self._buttons[pin] = pressed

    def light(self) -> int:
        """Read light sensor (0-65535)."""
        return self._light_value

    def _set_light(self, value: int):
        """Set light sensor value (called by emulator)."""
        self._light_value = max(0, min(65535, value))

    def update(self):
        """Update display."""
        self.display.update()


# Convenience functions for button reading
def pressed(button_pin: int) -> bool:
    """Check if button is pressed."""
    state = get_state()
    tufty = state.get("tufty2350")
    if tufty:
        return tufty.button(button_pin)
    return False


def read_light() -> int:
    """Read light sensor value."""
    state = get_state()
    tufty = state.get("tufty2350")
    if tufty:
        return tufty.light()
    return 32768
