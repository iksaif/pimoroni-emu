"""Base device configuration class."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class ButtonConfig:
    """Button configuration."""
    name: str
    key: str  # Keyboard key to map
    pin: int  # GPIO pin number


@dataclass
class BaseDevice:
    """Base class for device configurations."""

    # Device identification
    name: str = "Unknown Device"
    description: str = ""

    # Display configuration
    display_width: int = 320
    display_height: int = 240
    display_type: str = "tft"  # "tft" or "led_matrix"
    display_scale: int = 2  # Scale factor for pygame window

    # Color configuration
    color_depth: int = 16  # bits per pixel
    is_color: bool = True

    # Buttons
    buttons: List[ButtonConfig] = field(default_factory=list)

    # Touch support
    has_touch: bool = False

    # WiFi support
    has_wifi: bool = False

    # RGB LEDs
    num_rgb_leds: int = 0
    rgb_led_positions: List[Tuple[int, int]] = field(default_factory=list)

    # Rear lighting zones
    num_rear_zones: int = 0

    # Sensors
    has_light_sensor: bool = False
    has_accelerometer: bool = False

    # Battery
    has_battery: bool = False
    battery_capacity_mah: int = 0

    # Audio
    has_buzzer: bool = False

    # Storage
    has_sd_card: bool = False

    # Memory configuration
    heap_size: int = 256 * 1024   # Usable MicroPython heap in bytes (RP2350 default)
    has_psram: bool = False       # Whether device has PSRAM (adds 8MB)

    # E-ink specific
    is_eink: bool = False
    eink_colors: int = 2
    eink_refresh_time_ms: int = 1000

    # Button LEDs (white LEDs next to buttons)
    has_button_leds: bool = False

    # Status/Busy LED
    has_busy_led: bool = False

    # RTC (Real Time Clock)
    has_rtc: bool = False

    def get_window_size(self) -> Tuple[int, int]:
        """Get pygame window size (scaled)."""
        # Add padding for UI elements
        width = self.display_width * self.display_scale + 100
        height = self.display_height * self.display_scale + 80
        return (width, height)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Get display rectangle in window (x, y, w, h)."""
        win_w, win_h = self.get_window_size()
        disp_w = self.display_width * self.display_scale
        disp_h = self.display_height * self.display_scale
        x = (win_w - disp_w) // 2
        y = 40  # Space for top bar
        return (x, y, disp_w, disp_h)

    def get_button_by_key(self, key: str) -> Optional[ButtonConfig]:
        """Get button config by keyboard key."""
        for btn in self.buttons:
            if btn.key.lower() == key.lower():
                return btn
        return None

    def get_button_by_pin(self, pin: int) -> Optional[ButtonConfig]:
        """Get button config by GPIO pin."""
        for btn in self.buttons:
            if btn.pin == pin:
                return btn
        return None
