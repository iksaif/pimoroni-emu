"""Inky Impression device configurations (Raspberry Pi HAT).

These are e-ink displays that connect to Raspberry Pi via GPIO/SPI,
using the `inky` Python library (not MicroPython/PicoGraphics).
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class InkyImpression73Device(BaseDevice):
    """Inky Impression 7.3" - Spectra 6-color e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 7.3\" (Spectra)"
    description: str = "7.3\" e-ink (800x480, 6 colors) Raspberry Pi HAT"

    # Display: 800x480 Spectra 6 e-ink
    display_width: int = 800
    display_height: int = 480
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4  # 6 colors
    is_color: bool = True

    # No physical buttons (Raspberry Pi HAT)
    buttons: List[ButtonConfig] = field(default_factory=list)

    # No touch
    has_touch: bool = False

    # Uses Raspberry Pi's WiFi
    has_wifi: bool = True

    # No RGB LEDs on the HAT itself
    num_rgb_leds: int = 0

    # E-ink specific
    is_eink: bool = True
    eink_colors: int = 6  # Spectra 6: black, white, red, yellow, blue, green
    eink_refresh_time_ms: int = 20000  # ~20 seconds

    # Raspberry Pi device — no MicroPython heap tracking
    heap_size: int = 0
    is_raspberry_pi: bool = True
    library_type: str = "inky"

    def get_window_size(self) -> Tuple[int, int]:
        """Get pygame window size."""
        return (self.display_width + 60, self.display_height + 60)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Get display rectangle in window."""
        win_w, win_h = self.get_window_size()
        x = (win_w - self.display_width) // 2
        y = (win_h - self.display_height) // 2
        return (x, y, self.display_width, self.display_height)


@dataclass
class InkyImpression57Device(BaseDevice):
    """Inky Impression 5.7" - ACeP 7-color e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 5.7\""
    description: str = "5.7\" e-ink (600x448, 7 colors) Raspberry Pi HAT"

    display_width: int = 600
    display_height: int = 448
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 7
    eink_refresh_time_ms: int = 30000

    heap_size: int = 0
    is_raspberry_pi: bool = True
    library_type: str = "inky"

    def get_window_size(self) -> Tuple[int, int]:
        return (self.display_width + 60, self.display_height + 60)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        win_w, win_h = self.get_window_size()
        x = (win_w - self.display_width) // 2
        y = (win_h - self.display_height) // 2
        return (x, y, self.display_width, self.display_height)


@dataclass
class InkyImpression40Device(BaseDevice):
    """Inky Impression 4.0" - Compact 7-color e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 4.0\""
    description: str = "4.0\" e-ink (640x400, 7 colors) Raspberry Pi HAT"

    display_width: int = 640
    display_height: int = 400
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 7
    eink_refresh_time_ms: int = 30000

    heap_size: int = 0
    is_raspberry_pi: bool = True
    library_type: str = "inky"

    def get_window_size(self) -> Tuple[int, int]:
        return (self.display_width + 60, self.display_height + 60)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        win_w, win_h = self.get_window_size()
        x = (win_w - self.display_width) // 2
        y = (win_h - self.display_height) // 2
        return (x, y, self.display_width, self.display_height)


@dataclass
class InkyImpression133Device(BaseDevice):
    """Inky Impression 13.3" - Large Spectra e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 13.3\" (Spectra)"
    description: str = "13.3\" e-ink (1200x1600, 6 colors) Raspberry Pi HAT"

    display_width: int = 1200
    display_height: int = 1600
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 6
    eink_refresh_time_ms: int = 40000

    heap_size: int = 0
    is_raspberry_pi: bool = True
    library_type: str = "inky"

    def get_window_size(self) -> Tuple[int, int]:
        # Scale down for practical window size
        scale = 0.5
        return (int(self.display_width * scale) + 60, int(self.display_height * scale) + 60)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        win_w, win_h = self.get_window_size()
        scale = 0.5
        scaled_w = int(self.display_width * scale)
        scaled_h = int(self.display_height * scale)
        x = (win_w - scaled_w) // 2
        y = (win_h - scaled_h) // 2
        return (x, y, scaled_w, scaled_h)
