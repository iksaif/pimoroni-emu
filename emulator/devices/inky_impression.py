"""Inky device configurations (Raspberry Pi HAT).

These are e-ink displays that connect to Raspberry Pi via GPIO/SPI,
using the `inky` Python library (not MicroPython/PicoGraphics).

Covers the full Inky family: pHAT, wHAT, and Impression.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

from emulator.devices.base import BaseDevice, ButtonConfig

# --- Inky pHAT (small, Pi Zero form factor) ---

@dataclass
class InkyPHATDevice(BaseDevice):
    """Inky pHAT - Small e-ink display for Raspberry Pi Zero.

    Covers both the original (212x104) and SSD1608 (250x122) variants.
    Using the more common SSD1608 resolution as default.
    """

    name: str = "Inky pHAT"
    description: str = "2.13\" e-ink (250x122, B/W+accent) Raspberry Pi pHAT"

    display_width: int = 250
    display_height: int = 122
    display_type: str = "eink"
    display_scale: int = 1
    color_depth: int = 1
    is_color: bool = False

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 2
    eink_refresh_time_ms: int = 3000

    heap_size: int = 0
    is_raspberry_pi: bool = True
    library_type: str = "inky"

    def get_window_size(self) -> Tuple[int, int]:
        scale = 2  # Small display, scale up for usability
        return (self.display_width * scale + 60, self.display_height * scale + 60)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        scale = 2
        win_w, win_h = self.get_window_size()
        scaled_w = self.display_width * scale
        scaled_h = self.display_height * scale
        x = (win_w - scaled_w) // 2
        y = (win_h - scaled_h) // 2
        return (x, y, scaled_w, scaled_h)


# --- Inky wHAT (medium, full Pi HAT form factor) ---

@dataclass
class InkyWHATDevice(BaseDevice):
    """Inky wHAT - Medium e-ink display for Raspberry Pi.

    Covers the original, SSD1683, and JD79668 variants (all 400x300).
    """

    name: str = "Inky wHAT"
    description: str = "4.2\" e-ink (400x300, B/W+accent) Raspberry Pi HAT"

    display_width: int = 400
    display_height: int = 300
    display_type: str = "eink"
    display_scale: int = 1
    color_depth: int = 1
    is_color: bool = False

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 2
    eink_refresh_time_ms: int = 5000

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


# --- Inky Impression (large, multi-color) ---

@dataclass
class InkyImpression73Device(BaseDevice):
    """Inky Impression 7.3" - AC073TC1A 7-color e-ink HAT for Raspberry Pi.

    This is the older 7.3" variant using the AC073TC1A panel (7 colors
    including orange). The newer Spectra 6 variant uses the E673 panel
    (6 colors, no orange) — see InkyImpression73SpectraDevice.
    """

    name: str = "Inky Impression 7.3\""
    description: str = "7.3\" e-ink (800x480, 7 colors) Raspberry Pi HAT"

    # Display: 800x480 7-color e-ink (AC073TC1A)
    display_width: int = 800
    display_height: int = 480
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4  # 7 colors
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
    eink_colors: int = 7  # 7-color: black, white, green, blue, red, yellow, orange
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
class InkyImpression73SpectraDevice(BaseDevice):
    """Inky Impression 7.3" Spectra - E673 6-color e-ink HAT for Raspberry Pi.

    This is the newer 7.3" variant using the E673 / Spectra 6 panel
    (6 colors: black, white, yellow, red, blue, green — no orange).
    """

    name: str = "Inky Impression 7.3\" (Spectra)"
    description: str = "7.3\" e-ink (800x480, 6 colors) Raspberry Pi HAT"

    display_width: int = 800
    display_height: int = 480
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 6  # Spectra 6: black, white, yellow, red, blue, green
    eink_refresh_time_ms: int = 20000

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
class InkyImpression40SpectraDevice(BaseDevice):
    """Inky Impression 4.0" Spectra - E640 6-color e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 4.0\" (Spectra)"
    description: str = "4.0\" e-ink (600x400, 6 colors) Raspberry Pi HAT"

    display_width: int = 600
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
    eink_colors: int = 6  # Spectra 6: black, white, yellow, red, blue, green
    eink_refresh_time_ms: int = 20000

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
    """Inky Impression 13.3" - EL133UF1 Spectra 6-color e-ink HAT for Raspberry Pi."""

    name: str = "Inky Impression 13.3\" (Spectra)"
    description: str = "13.3\" e-ink (1600x1200, 6 colors) Raspberry Pi HAT"

    display_width: int = 1600
    display_height: int = 1200
    display_type: str = "eink_color"
    display_scale: int = 1
    color_depth: int = 4
    is_color: bool = True

    buttons: List[ButtonConfig] = field(default_factory=list)
    has_touch: bool = False
    has_wifi: bool = True
    num_rgb_leds: int = 0

    is_eink: bool = True
    eink_colors: int = 6  # Spectra 6: black, white, yellow, red, blue, green
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
