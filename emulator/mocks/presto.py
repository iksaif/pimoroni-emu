"""Mock implementation of Presto device module."""

from collections import namedtuple
from typing import Tuple
from emulator import get_state
from emulator.mocks.base import trace_log
from emulator.mocks.picographics import PicoGraphics, DISPLAY_PRESTO, PEN_RGB565
from emulator.mocks.touch import FT6236


# LED positions (7 SK6812 LEDs around the edge)
NUM_LEDS = 7

# Touch namedtuple for touch properties
Touch = namedtuple("touch", ("x", "y", "touched"))


class Presto:
    """Presto device controller."""

    NUM_LEDS = 7
    LED_PIN = 33

    def __init__(
        self,
        full_res: bool = False,
        palette: bool = False,
        ambient_light: bool = False,
        direct_to_fb: bool = False,
        layers: int = None,
    ):
        self._full_res = full_res
        self._ambient_light = ambient_light
        self._connected = False

        # Touch controller
        self.touch = FT6236(full_res=full_res)

        # LED strip data
        self._leds = [(0, 0, 0)] * NUM_LEDS
        self._led_brightness = 1.0

        # Create display
        self.display = PicoGraphics(
            display=DISPLAY_PRESTO,
            pen_type=PEN_RGB565,
        )
        self.width, self.height = self.display.get_bounds()

        # Create a raw framebuffer for direct access
        # This is 480x480 RGB565 (2 bytes per pixel)
        self._presto_buffer = bytearray(self.width * self.height * 2)

        # Register with emulator
        get_state()["presto"] = self
        trace_log("Presto", f"Initialized, full_res={full_res}")

    @property
    def presto(self):
        """Get raw framebuffer for direct memory access."""
        return self._presto_buffer

    @property
    def touch_a(self) -> Touch:
        """Get primary touch point."""
        return Touch(self.touch.x, self.touch.y, self.touch.state)

    @property
    def touch_b(self) -> Touch:
        """Get secondary touch point."""
        return Touch(self.touch.x2, self.touch.y2, self.touch.state2)

    @property
    def touch_delta(self) -> Tuple[float, float]:
        """Get multi-touch distance and angle."""
        return self.touch.distance, self.touch.angle

    def touch_poll(self):
        """Poll touch state."""
        self.touch.poll()

    def connect(self, ssid: str = None, password: str = None, timeout: int = 30) -> bool:
        """Connect to WiFi network."""
        from emulator.mocks.network import WLAN, STA_IF

        wlan = WLAN(STA_IF)
        wlan.active(True)

        if ssid:
            wlan.connect(ssid, password or "")
            self._connected = wlan.isconnected()
        else:
            # Use saved credentials (simulated)
            self._connected = True

        return self._connected

    def set_backlight(self, brightness: float):
        """Set display backlight (0.0 to 1.0)."""
        self.display.set_backlight(brightness)

    def auto_ambient_leds(self, enable: bool):
        """Enable/disable automatic ambient LED control."""
        self._ambient_light = enable

    # LED strip control
    def set_led_rgb(self, index: int, r: int, g: int, b: int):
        """Set individual LED color."""
        if 0 <= index < NUM_LEDS:
            self._leds[index] = (r, g, b)

    def set_led_hsv(self, index: int, h: float, s: float, v: float):
        """Set individual LED color from HSV."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_led_rgb(index, int(r * 255), int(g * 255), int(b * 255))

    def set_all_leds_rgb(self, r: int, g: int, b: int):
        """Set all LEDs to same color."""
        for i in range(NUM_LEDS):
            self._leds[i] = (r, g, b)

    def set_all_leds_hsv(self, h: float, s: float, v: float):
        """Set all LEDs to same HSV color."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_all_leds_rgb(int(r * 255), int(g * 255), int(b * 255))

    def set_led_brightness(self, brightness: float):
        """Set LED brightness (0.0 to 1.0)."""
        self._led_brightness = max(0.0, min(1.0, brightness))

    def update_leds(self):
        """Update LED strip."""
        trace_log("Presto", f"Update LEDs: {self._leds}")

    def get_leds(self) -> list:
        """Get current LED colors (for emulator rendering)."""
        factor = self._led_brightness
        return [
            (int(r * factor), int(g * factor), int(b * factor))
            for r, g, b in self._leds
        ]

    # Update
    def update(self):
        """Update display and LEDs."""
        self.display.update()
        self.update_leds()
        self.touch.poll()

    def partial_update(self, x: int, y: int, w: int, h: int):
        """Partial display update."""
        self.display.partial_update(x, y, w, h)
        self.touch.poll()

    def clear(self):
        """Clear display."""
        self.display.clear()
        self.display.update()


class Buzzer:
    """Mock buzzer for Presto with real audio output via pygame."""

    def __init__(self, pin: int = 43):
        self._pin = pin
        self._freq = 0
        self._duty = 0
        self._channel = None
        self._sound = None
        self._audio_init = False
        get_state()["buzzer"] = self

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
        import math
        sample_rate = 44100
        duration_samples = sample_rate  # 1 second looping buffer
        buf = array.array('h')  # signed 16-bit
        amplitude = 16000
        period = sample_rate / freq if freq > 0 else 1
        for i in range(duration_samples):
            # Square wave with variable duty cycle
            phase = (i % int(period)) / period if period > 0 else 0
            val = amplitude if phase < duty else -amplitude
            buf.append(int(val))
        return pygame.mixer.Sound(buffer=buf)

    def set_tone(self, freq: int, duty: float = 0.5):
        """Set buzzer tone frequency and duty cycle."""
        old_freq = self._freq
        self._freq = freq
        self._duty = duty
        trace_log("Buzzer", f"set_tone({freq}, {duty})")

        if not self._ensure_audio():
            return

        # Stop current sound
        if self._channel and self._channel.get_busy():
            self._channel.stop()

        if freq > 20:
            import pygame
            self._sound = self._generate_tone(freq, duty)
            self._channel = self._sound.play(loops=-1)
        else:
            self._sound = None

    def play_tone(self, freq: int, duration: float = 0.1, duty: float = 0.5):
        """Play a tone for a duration."""
        self.set_tone(freq, duty)
        import time
        time.sleep(duration)
        self.set_tone(0)

    def stop(self):
        """Stop the buzzer."""
        self.set_tone(0)


class WiFi:
    """WiFi helper for Presto."""

    @staticmethod
    def connect(ssid: str, password: str = "", timeout: int = 30) -> bool:
        """Connect to WiFi."""
        from emulator.mocks.network import WLAN, STA_IF
        wlan = WLAN(STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)
        return wlan.isconnected()

    @staticmethod
    def is_connected() -> bool:
        """Check if connected."""
        state = get_state()
        wlan = state.get("wlan")
        return wlan.isconnected() if wlan else False

    @staticmethod
    def ip_address() -> str:
        """Get IP address."""
        state = get_state()
        wlan = state.get("wlan")
        return wlan.ifconfig()[0] if wlan else "0.0.0.0"
