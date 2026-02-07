"""Badger 2350 device configuration."""

from dataclasses import dataclass, field
from typing import List
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class Badger2350Device(BaseDevice):
    """Badger 2350 - 2.9" e-ink badge."""

    name: str = "Badger 2350"
    description: str = "2.9\" e-ink monochrome badge with buttons"

    # Display: 296x128 e-ink (grayscale)
    display_width: int = 296
    display_height: int = 128
    display_type: str = "eink"
    display_scale: int = 2
    color_depth: int = 1  # 1-bit monochrome (or 2-bit for grayscale)
    is_color: bool = False

    # Buttons (5 front buttons, same layout as others)
    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=12),
        ButtonConfig(name="B", key="s", pin=13),
        ButtonConfig(name="C", key="d", pin=14),
        ButtonConfig(name="UP", key="up", pin=15),
        ButtonConfig(name="DOWN", key="down", pin=11),
    ])

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
    eink_refresh_time_ms: int = 500  # Simulated refresh time
