"""Inky Frame device configurations (MicroPython/PicoGraphics)."""

from dataclasses import dataclass, field
from typing import List, Tuple
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class InkyFrame73Device(BaseDevice):
    """Inky Frame 7.3" - RP2350-based e-ink display with PicoGraphics."""

    name: str = "Inky Frame 7.3\""
    description: str = "7.3\" e-ink (800x480, 6 colors) with RP2350 Pico 2 W"

    # Display: 800x480 Spectra 6 e-ink
    display_width: int = 800
    display_height: int = 480
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4  # 6 colors = ~2.5 bits, use 4-bit palette
    is_color: bool = True

    # 5 buttons with LED indicators
    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=0),
        ButtonConfig(name="B", key="s", pin=1),
        ButtonConfig(name="C", key="d", pin=2),
        ButtonConfig(name="D", key="f", pin=3),
        ButtonConfig(name="E", key="g", pin=4),
    ])

    # No touch
    has_touch: bool = False

    # WiFi via Pico 2 W
    has_wifi: bool = True

    # Button LEDs (white LEDs next to each button)
    num_rgb_leds: int = 0  # Not RGB, just white LEDs
    has_button_leds: bool = True

    # Busy/Activity LED (with flag icon)
    has_busy_led: bool = True

    # Has RTC
    has_rtc: bool = True

    # Has SD card
    has_sd_card: bool = True

    # Battery support
    has_battery: bool = True
    battery_capacity_mah: int = 0  # External, user-provided

    # RP2350 with PSRAM
    has_psram: bool = True

    # E-ink specific
    is_eink: bool = True
    eink_colors: int = 6  # Spectra 6: black, white, red, yellow, blue, green
    eink_refresh_time_ms: int = 20000  # ~20 seconds

    def get_window_size(self) -> Tuple[int, int]:
        """Get pygame window size."""
        return (self.display_width + 100, self.display_height + 80)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Get display rectangle in window."""
        win_w, win_h = self.get_window_size()
        x = (win_w - self.display_width) // 2
        y = 40
        return (x, y, self.display_width, self.display_height)


@dataclass
class InkyFrame58Device(BaseDevice):
    """Inky Frame 5.8" - Older RP2040-based e-ink display."""

    name: str = "Inky Frame 5.8\""
    description: str = "5.8\" e-ink (600x448, 7 colors) with RP2040"

    display_width: int = 600
    display_height: int = 448
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=0),
        ButtonConfig(name="B", key="s", pin=1),
        ButtonConfig(name="C", key="d", pin=2),
        ButtonConfig(name="D", key="f", pin=3),
        ButtonConfig(name="E", key="g", pin=4),
    ])

    has_touch: bool = False
    has_wifi: bool = True
    has_button_leds: bool = True
    has_busy_led: bool = True
    has_rtc: bool = True
    has_sd_card: bool = True
    has_battery: bool = True

    # RP2040, no PSRAM
    heap_size: int = 192 * 1024

    is_eink: bool = True
    eink_colors: int = 7  # ACeP: black, white, red, green, blue, yellow, orange
    eink_refresh_time_ms: int = 30000


@dataclass
class InkyFrame40Device(BaseDevice):
    """Inky Frame 4.0" - Compact e-ink display."""

    name: str = "Inky Frame 4.0\""
    description: str = "4.0\" e-ink (640x400, 7 colors) with RP2040"

    display_width: int = 640
    display_height: int = 400
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=0),
        ButtonConfig(name="B", key="s", pin=1),
        ButtonConfig(name="C", key="d", pin=2),
        ButtonConfig(name="D", key="f", pin=3),
        ButtonConfig(name="E", key="g", pin=4),
    ])

    has_touch: bool = False
    has_wifi: bool = True
    has_button_leds: bool = True
    has_busy_led: bool = True
    has_rtc: bool = True
    has_sd_card: bool = True
    has_battery: bool = True

    # RP2040, no PSRAM
    heap_size: int = 192 * 1024

    is_eink: bool = True
    eink_colors: int = 7
    eink_refresh_time_ms: int = 30000
