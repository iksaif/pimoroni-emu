"""Badger 2350 device configuration."""

from dataclasses import dataclass, field
from typing import List, Tuple

from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class Badger2350Device(BaseDevice):
    """Badger 2350 - 2.9" e-ink badge."""

    name: str = "Badger 2350"
    description: str = "2.9\" e-ink monochrome badge with buttons"

    # Display: 264x176 e-ink (matches app coordinate system and spec sheet)
    display_width: int = 264
    display_height: int = 176
    display_type: str = "eink"
    display_scale: int = 1
    color_depth: int = 1
    is_color: bool = False

    # Front buttons: A/B/C along bottom, UP/DOWN on right side.
    # USR (GPIO 0) is the boot/home button on the back, included here
    # so the emulator can show and click it.
    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A",    key="a",   pin=12),
        ButtonConfig(name="B",    key="s",   pin=13),
        ButtonConfig(name="C",    key="d",   pin=14),
        ButtonConfig(name="UP",   key="up",  pin=15),
        ButtonConfig(name="DOWN", key="down", pin=11),
        ButtonConfig(name="USR",  key="u",   pin=0),
    ])

    # Use the Badger-specific button layout in the emulator window.
    badger_button_layout: bool = True

    # No touch
    has_touch: bool = False

    # WiFi/Bluetooth via ESP32 module
    has_wifi: bool = True

    # No front RGB LEDs
    num_rgb_leds: int = 0

    # 4 rear lighting zones
    num_rear_zones: int = 4

    # No sensors
    has_light_sensor: bool = False
    has_accelerometer: bool = False

    # Built-in 1000mAh battery
    has_battery: bool = True
    battery_capacity_mah: int = 1000

    # No buzzer
    has_buzzer: bool = False

    # No SD card
    has_sd_card: bool = False

    # E-ink specific settings
    is_eink: bool = True
    eink_refresh_time_ms: int = 500

    def get_window_size(self) -> Tuple[int, int]:
        """Window sized for Badger layout:
          left margin | display | gap | UP/DOWN buttons | right margin
          top status  | display | gap | A/B/C buttons   | bottom margin
        """
        s = self.display_scale
        w = 10 + self.display_width * s + 15 + 54 + 6
        h = 40 + self.display_height * s + 12 + 38 + 8
        return (w, h)

    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Display is top-left, leaving room on the right for UP/DOWN."""
        s = self.display_scale
        return (10, 40, self.display_width * s, self.display_height * s)
