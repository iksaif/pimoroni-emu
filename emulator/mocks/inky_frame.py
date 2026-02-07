"""Mock implementation of the inky_frame MicroPython module.

This provides the button and LED control API used by Inky Frame devices.
The inky_frame module is baked into Pimoroni's MicroPython firmware.
"""

from typing import Optional, Callable
from emulator import get_state


class LED:
    """White LED control (PWM capable)."""

    def __init__(self, name: str, pin: int = 0):
        self.name = name
        self.pin = pin
        self._brightness = 0  # 0-100
        self._state = False

        # Register with emulator state
        state = get_state()
        if "leds" not in state:
            state["leds"] = {}
        state["leds"][name] = self

    def on(self):
        """Turn LED on at full brightness."""
        self._state = True
        self._brightness = 100
        self._notify()

    def off(self):
        """Turn LED off."""
        self._state = False
        self._brightness = 0
        self._notify()

    def brightness(self, value: int):
        """Set LED brightness (0-100)."""
        self._brightness = max(0, min(100, value))
        self._state = self._brightness > 0
        self._notify()

    def toggle(self):
        """Toggle LED state."""
        if self._state:
            self.off()
        else:
            self.on()

    def _notify(self):
        """Notify emulator of state change."""
        state = get_state()
        if state.get("trace"):
            print(f"[LED] {self.name}: {'ON' if self._state else 'OFF'} ({self._brightness}%)")

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def value(self) -> int:
        return self._brightness


class Button:
    """Button with integrated LED."""

    def __init__(self, pin: int, name: str = "", invert: bool = True):
        self.pin = pin
        self.name = name or f"button_{pin}"
        self.invert = invert
        self._pressed = False
        self._led = LED(f"button_{name.lower()}_led", pin)

        # Interrupt callback
        self._callback: Optional[Callable] = None

        # Register with emulator state
        state = get_state()
        if "buttons" not in state:
            state["buttons"] = {}
        state["buttons"][pin] = self

    def read(self) -> bool:
        """Read raw button state."""
        return self._pressed

    def is_pressed(self) -> bool:
        """Check if button is currently pressed."""
        return self._pressed

    @property
    def is_held(self) -> bool:
        """Check if button is being held."""
        return self._pressed

    # LED control methods
    def led_on(self):
        """Turn the button's LED on."""
        self._led.on()

    def led_off(self):
        """Turn the button's LED off."""
        self._led.off()

    def led_brightness(self, value: int):
        """Set the button's LED brightness (0-100)."""
        self._led.brightness(value)

    def led_toggle(self):
        """Toggle the button's LED."""
        self._led.toggle()

    @property
    def led(self) -> LED:
        """Access the button's LED directly."""
        return self._led

    # Internal methods for emulator
    def _set_pressed(self, pressed: bool):
        """Set button state (called by emulator)."""
        was_pressed = self._pressed
        self._pressed = pressed

        # Trigger callback on press
        if pressed and not was_pressed and self._callback:
            self._callback(self)


# Create the 5 buttons (A-E)
button_a = Button(pin=0, name="A")
button_b = Button(pin=1, name="B")
button_c = Button(pin=2, name="C")
button_d = Button(pin=3, name="D")
button_e = Button(pin=4, name="E")

# Busy/Activity LED (the one with the flag icon)
led_busy = LED("busy", pin=6)

# Activity LED alias
led_activity = led_busy

# WiFi LED (if present)
led_wifi = LED("wifi", pin=7)

# Additional convenience aliases
led_connect = led_wifi


def woken_by_button() -> bool:
    """Check if device was woken by a button press."""
    # In emulator, always return False (not woken from sleep)
    return False


def woken_by_rtc() -> bool:
    """Check if device was woken by RTC alarm."""
    return False


def woken_by_ext_trigger() -> bool:
    """Check if device was woken by external trigger."""
    return False


def sleep_for(minutes: int):
    """Put device into deep sleep for specified minutes.

    In emulator, this just pauses execution briefly.
    """
    import time
    state = get_state()
    if state.get("trace"):
        print(f"[inky_frame] sleep_for({minutes} minutes) - simulating brief pause")
    time.sleep(0.1)  # Brief pause in emulator


def turn_off():
    """Turn off the device completely.

    In emulator, this stops the running app.
    """
    state = get_state()
    if state.get("trace"):
        print("[inky_frame] turn_off() called - stopping emulator")
    state["running"] = False


# RTC functions
class RTC:
    """Real-time clock interface."""

    def __init__(self):
        pass

    def datetime(self, dt=None):
        """Get or set datetime.

        Returns tuple: (year, month, day, weekday, hour, minute, second, subsecond)
        """
        import time
        if dt is not None:
            # Setting time - ignore in emulator
            return

        t = time.localtime()
        return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_wday,
                t.tm_hour, t.tm_min, t.tm_sec, 0)

    def set_alarm(self, second=None, minute=None, hour=None, day=None):
        """Set RTC alarm for wakeup."""
        state = get_state()
        if state.get("trace"):
            print(f"[RTC] Alarm set: day={day}, hour={hour}, minute={minute}, second={second}")

    def clear_alarm(self):
        """Clear RTC alarm."""
        pass

    def alarm_triggered(self) -> bool:
        """Check if alarm was triggered."""
        return False


# Create RTC instance
rtc = RTC()


# Network helpers
def network_connect(ssid: str, password: str, timeout: int = 30) -> bool:
    """Connect to WiFi network.

    In emulator, this simulates a successful connection.
    """
    state = get_state()
    if state.get("trace"):
        print(f"[inky_frame] Connecting to WiFi: {ssid}")

    led_wifi.on()
    return True


def network_disconnect():
    """Disconnect from WiFi."""
    led_wifi.off()


def is_network_connected() -> bool:
    """Check if WiFi is connected."""
    return led_wifi.is_on
