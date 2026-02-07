"""Presto device configuration."""

from dataclasses import dataclass, field
from typing import List, Tuple
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class PrestoDevice(BaseDevice):
    """Presto - 4" touchscreen desktop display."""

    name: str = "Presto"
    description: str = "4\" IPS touchscreen desktop companion with WiFi"

    # Display: 480x480 IPS touchscreen
    display_width: int = 480
    display_height: int = 480
    display_type: str = "tft"
    display_scale: int = 1  # Can be overridden via --scale CLI argument
    color_depth: int = 16
    is_color: bool = True

    # No physical buttons (touch only)
    buttons: List[ButtonConfig] = field(default_factory=list)

    # Capacitive touch
    has_touch: bool = True

    # WiFi via RM2 module (CYW43439)
    has_wifi: bool = True

    # 7 SK6812 RGB LEDs around the edge
    num_rgb_leds: int = 7
    # LED positions relative to display center (in base units, multiplied by display_scale)
    # These put LEDs ~20 pixels outside the display edge at any scale
    rgb_led_positions: List[Tuple[int, int]] = field(default_factory=lambda: [
        (-260, -200),   # Top left
        (-260, 0),      # Left
        (-260, 200),    # Bottom left
        (0, 260),       # Bottom center
        (260, 200),     # Bottom right
        (260, 0),       # Right
        (260, -200),    # Top right
    ])

    # No rear zones (desktop device)
    num_rear_zones: int = 0

    # No sensors
    has_light_sensor: bool = False
    has_accelerometer: bool = False

    # Optional battery (JST connector)
    has_battery: bool = False  # Not included by default
    battery_capacity_mah: int = 0

    # Piezo buzzer
    has_buzzer: bool = True

    # microSD slot
    has_sd_card: bool = True

    # RP2350 with 8MB PSRAM
    has_psram: bool = True

    def get_window_size(self) -> Tuple[int, int]:
        """Get pygame window size (with space for LEDs)."""
        scaled_width = self.display_width * self.display_scale
        scaled_height = self.display_height * self.display_scale
        # Scale margin for RGB LEDs to match display scale
        margin_x = 120 * self.display_scale
        margin_y = 100 * self.display_scale
        return (scaled_width + margin_x, scaled_height + margin_y)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Get display rectangle in window (scaled)."""
        win_w, win_h = self.get_window_size()
        scaled_width = self.display_width * self.display_scale
        scaled_height = self.display_height * self.display_scale
        x = (win_w - scaled_width) // 2
        y = (win_h - scaled_height) // 2
        return (x, y, scaled_width, scaled_height)
