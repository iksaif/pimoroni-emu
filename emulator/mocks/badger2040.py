"""Mock implementation of the badger2040 module.

Badger 2040 is an e-ink badge with 296x128 display and 5 front buttons.
"""

from emulator import get_state
from emulator.mocks.picographics import PicoGraphics, DISPLAY_BADGER_2350, PEN_1BIT


# Display dimensions
WIDTH = 296
HEIGHT = 128

# Update speeds for e-ink
UPDATE_NORMAL = 0
UPDATE_MEDIUM = 1
UPDATE_FAST = 2
UPDATE_TURBO = 3

# Button constants
BUTTON_A = 0
BUTTON_B = 1
BUTTON_C = 2
BUTTON_UP = 3
BUTTON_DOWN = 4
BUTTON_USER = 5

# Button pins (for IRQ handling)
from emulator.mocks.machine import Pin

BUTTONS = {
    BUTTON_A: Pin(12),
    BUTTON_B: Pin(13),
    BUTTON_C: Pin(14),
    BUTTON_UP: Pin(15),
    BUTTON_DOWN: Pin(11),
}


def is_wireless() -> bool:
    """Check if device has wireless capability."""
    return True  # Badger 2040 W has WiFi


def woken_by_button() -> bool:
    """Check if device was woken by a button press."""
    return False


def pressed_to_wake(button: int) -> bool:
    """Check if specific button was pressed to wake."""
    return False


def reset_pressed_to_wake():
    """Reset the pressed-to-wake flags."""
    pass


def pico_rtc_to_pcf():
    """Sync Pico RTC to PCF8523 RTC (stub)."""
    pass


def pcf_to_pico_rtc():
    """Sync PCF8523 RTC to Pico RTC (stub)."""
    pass


class Badger2040:
    """Badger 2040 e-ink badge controller."""

    def __init__(self):
        self._update_speed = UPDATE_NORMAL
        self._led_brightness = 0
        self._thickness = 1
        self._font = "bitmap8"

        # Create the e-ink display
        self.display = PicoGraphics(
            display=DISPLAY_BADGER_2350,
            pen_type=PEN_1BIT,
        )

        # Button state
        self._buttons = {
            BUTTON_A: False,
            BUTTON_B: False,
            BUTTON_C: False,
            BUTTON_UP: False,
            BUTTON_DOWN: False,
            BUTTON_USER: False,
        }

        # Register with emulator state
        state = get_state()
        state["badger2040"] = self

        if state.get("trace"):
            print("[Badger2040] Initialized")

    def led(self, brightness: int):
        """Set the LED brightness (0-255)."""
        self._led_brightness = max(0, min(255, brightness))

    def set_update_speed(self, speed: int):
        """Set e-ink update speed."""
        self._update_speed = speed

    def update(self):
        """Update the display."""
        self.display.update()

    def set_thickness(self, thickness: int):
        """Set line/text thickness."""
        self._thickness = max(1, thickness)
        self.display.set_thickness(thickness)

    def set_pen(self, pen: int):
        """Set drawing pen (0=black, 15=white for e-ink)."""
        self.display.set_pen(pen)

    def set_font(self, font: str):
        """Set text font."""
        self._font = font
        self.display.set_font(font)

    def clear(self):
        """Clear display with current pen."""
        self.display.clear()

    def pixel(self, x: int, y: int):
        """Draw a single pixel."""
        self.display.pixel(x, y)

    def line(self, x1: int, y1: int, x2: int, y2: int, thickness: int = None):
        """Draw a line."""
        if thickness is None:
            thickness = self._thickness
        self.display.line(x1, y1, x2, y2, thickness)

    def rectangle(self, x: int, y: int, w: int, h: int):
        """Draw a filled rectangle."""
        self.display.rectangle(x, y, w, h)

    def circle(self, x: int, y: int, r: int):
        """Draw a filled circle."""
        self.display.circle(x, y, r)

    def text(self, text: str, x: int, y: int, width: int = WIDTH, scale: float = 1.0):
        """Draw text."""
        return self.display.text(text, x, y, wordwrap=width, scale=scale)

    def measure_text(self, text: str, scale: float = 1.0) -> int:
        """Measure text width."""
        return self.display.measure_text(text, scale=scale)

    def image(self, data: bytes, w: int, h: int, x: int, y: int):
        """Draw a 1-bit image from packed bytes."""
        for row in range(h):
            for col in range(w):
                byte_idx = (row * w + col) // 8
                bit_idx = 7 - ((row * w + col) % 8)
                if byte_idx < len(data) and (data[byte_idx] & (1 << bit_idx)):
                    self.display.pixel(x + col, y + row)

    def glyph(self, char: int, x: int, y: int, scale: float = 1.0):
        """Draw a single glyph."""
        self.display.character(char, x, y, scale)

    # Button handling
    def pressed(self, button: int) -> bool:
        """Check if button is currently pressed."""
        state = get_state()
        buttons = state.get("button_state", {})
        return buttons.get(button, False)

    def pressed_any(self) -> bool:
        """Check if any button is pressed."""
        state = get_state()
        buttons = state.get("button_state", {})
        return any(buttons.values())

    # Power management
    def halt(self):
        """Halt the device to save power (in emulator, just a small delay)."""
        import time
        time.sleep(0.1)

    def keepalive(self):
        """Keep the device powered on."""
        pass

    def turn_off(self):
        """Turn off the device."""
        pass

    # Invert display
    def invert(self, invert: bool):
        """Invert display colors."""
        self._inverted = invert
        if self.display and self.display._buffer:
            for y in range(len(self.display._buffer)):
                for x in range(len(self.display._buffer[y])):
                    val = self.display._buffer[y][x]
                    self.display._buffer[y][x] = 15 - val if val <= 15 else val ^ 0xFFFFFF

    def partial_update(self, x: int, y: int, w: int, h: int):
        """Partial display update."""
        self.display.partial_update(x, y, w, h)

    # Busy checking
    def is_busy(self) -> bool:
        """Check if display is busy updating."""
        return False

    def wait_for_idle(self):
        """Wait for display to finish updating."""
        pass

    @property
    def width(self) -> int:
        return WIDTH

    @property
    def height(self) -> int:
        return HEIGHT

    def get_bounds(self):
        """Get display bounds as (width, height)."""
        return (WIDTH, HEIGHT)

    def connect(self):
        """Connect to WiFi (stub)."""
        pass

    def isconnected(self) -> bool:
        """Check if connected to WiFi."""
        state = get_state()
        wlan = state.get("wlan")
        return wlan.isconnected() if wlan else False
