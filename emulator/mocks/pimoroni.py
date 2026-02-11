"""Mock implementation of Pimoroni's pimoroni module.

Contains hardware helpers like Button, RGBLED, Buzzer, etc.
"""

from typing import Callable, Optional
import time as _time
from emulator import get_state


class Button:
    """Hardware button with interrupt support."""

    def __init__(self, pin: int, invert: bool = True, repeat_time: int = 200, hold_time: int = 1000):
        self._pin = pin
        self._invert = invert
        self._repeat_time = repeat_time
        self._hold_time = hold_time
        self._pressed = False
        self._last_press = 0
        self._press_start = 0

        # Register with emulator
        state = get_state()
        if "buttons" not in state:
            state["buttons"] = {}
        state["buttons"][pin] = self

    def read(self) -> bool:
        """Read current button state."""
        return self._pressed

    def raw(self) -> bool:
        """Read raw button state (before debounce)."""
        return self._pressed

    def is_pressed(self) -> bool:
        """Check if button is currently pressed."""
        return self._pressed

    # Methods called by emulator
    def _press(self):
        """Called when button is pressed."""
        self._pressed = True
        self._press_start = _time.time()
        if get_state().get("trace"):
            print(f"[Button] Pin {self._pin} pressed")

    def _release(self):
        """Called when button is released."""
        self._pressed = False
        if get_state().get("trace"):
            print(f"[Button] Pin {self._pin} released")


class RGBLED:
    """RGB LED controller."""

    def __init__(self, r_pin: int, g_pin: int, b_pin: int, invert: bool = True):
        self._r_pin = r_pin
        self._g_pin = g_pin
        self._b_pin = b_pin
        self._invert = invert
        self._r = 0
        self._g = 0
        self._b = 0

        # Register with emulator
        state = get_state()
        if "rgbleds" not in state:
            state["rgbleds"] = []
        state["rgbleds"].append(self)

    def set_rgb(self, r: int, g: int, b: int):
        """Set LED color (0-255 per channel)."""
        self._r = max(0, min(255, r))
        self._g = max(0, min(255, g))
        self._b = max(0, min(255, b))
        if get_state().get("trace"):
            print(f"[RGBLED] Set to ({r}, {g}, {b})")

    def set_hsv(self, h: float, s: float, v: float):
        """Set LED color from HSV (0-1 range)."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_rgb(int(r * 255), int(g * 255), int(b * 255))

    def set_brightness(self, brightness: int):
        """Set overall brightness (0-255)."""
        factor = brightness / 255.0
        self._r = int(self._r * factor)
        self._g = int(self._g * factor)
        self._b = int(self._b * factor)

    def off(self):
        """Turn LED off."""
        self.set_rgb(0, 0, 0)

    def get_rgb(self) -> tuple:
        """Get current RGB values."""
        return (self._r, self._g, self._b)


class Buzzer:
    """Piezo buzzer controller with audio output via pygame.mixer."""

    def __init__(self, pin: int):
        self._pin = pin
        self._frequency = 0
        self._duty = 0
        self._channel = None
        self._sound = None
        self._audio_init = False

    def _ensure_audio(self):
        """Lazy-init pygame mixer for audio output."""
        if self._audio_init:
            return True
        if get_state().get("headless"):
            return False
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._audio_init = True
            return True
        except Exception:
            return False

    def _generate_tone(self, freq: int, duty: float = 0.5):
        """Generate a square wave tone as a pygame Sound."""
        import pygame
        import array
        sample_rate = 44100
        duration_samples = sample_rate  # 1 second looping buffer
        buf = array.array('h')  # signed 16-bit
        amplitude = 16000
        period = sample_rate / freq if freq > 0 else 1
        for i in range(duration_samples):
            phase = (i % int(period)) / period if period > 0 else 0
            val = amplitude if phase < duty else -amplitude
            buf.append(int(val))
        return pygame.mixer.Sound(buffer=buf)

    def set_tone(self, frequency: int, duty: float = 0.5):
        """Set buzzer tone."""
        self._frequency = frequency
        self._duty = duty
        if get_state().get("trace"):
            print(f"[Buzzer] Tone {frequency}Hz, duty {duty}")

        if not self._ensure_audio():
            return

        if self._channel and self._channel.get_busy():
            self._channel.stop()

        if frequency > 20:
            import pygame
            self._sound = self._generate_tone(frequency, duty)
            self._channel = self._sound.play(loops=-1)
        else:
            self._sound = None

    def stop(self):
        """Stop buzzer."""
        self.set_tone(0)


class Analog:
    """Analog input reader."""

    def __init__(self, pin: int, amplifier_gain: float = 1.0, resistor: float = 0.0):
        self._pin = pin
        self._gain = amplifier_gain
        self._resistor = resistor
        self._value = 0.5  # Default middle value

    def read_voltage(self) -> float:
        """Read voltage (0.0 to 3.3V)."""
        return self._value * 3.3

    def read_current(self) -> float:
        """Read current (if resistor configured)."""
        if self._resistor > 0:
            return self.read_voltage() / self._resistor
        return 0.0

    def _set_value(self, value: float):
        """Set mock value (for testing)."""
        self._value = max(0.0, min(1.0, value))


# RP2350 specific
class PimoroniI2C:
    """Pimoroni's I2C wrapper with default pins."""

    def __init__(self, sda: int = 4, scl: int = 5, baudrate: int = 400000):
        from emulator.mocks.machine import I2C, Pin
        self._i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=baudrate)

    def scan(self):
        return self._i2c.scan()

    def readfrom(self, addr, nbytes, stop=True):
        return self._i2c.readfrom(addr, nbytes, stop)

    def writeto(self, addr, buf, stop=True):
        return self._i2c.writeto(addr, buf, stop)

    def readfrom_mem(self, addr, memaddr, nbytes, addrsize=8):
        return self._i2c.readfrom_mem(addr, memaddr, nbytes, addrsize=addrsize)

    def writeto_mem(self, addr, memaddr, buf, addrsize=8):
        return self._i2c.writeto_mem(addr, memaddr, buf, addrsize=addrsize)


# ShiftRegister for LED control
class ShiftRegister:
    """Shift register for GPIO expansion."""

    def __init__(self, clk: int, data: int, latch: int, n_bits: int = 8):
        self._clk = clk
        self._data = data
        self._latch = latch
        self._n_bits = n_bits
        self._value = 0

    def write(self, value: int):
        """Write value to shift register."""
        self._value = value & ((1 << self._n_bits) - 1)

    def read(self) -> int:
        """Read current value."""
        return self._value
