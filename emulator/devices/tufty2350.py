"""Tufty 2350 device configuration."""

from dataclasses import dataclass, field
from typing import List
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class Tufty2350Device(BaseDevice):
    """Tufty 2350 - 2.8" IPS TFT badge."""

    name: str = "Tufty 2350"
    description: str = "2.8\" IPS TFT color badge with buttons"

    # Display: 320x240 IPS TFT
    display_width: int = 320
    display_height: int = 240
    display_type: str = "tft"
    display_scale: int = 2
    color_depth: int = 16
    is_color: bool = True

    # Buttons (5 front buttons)
    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=7),
        ButtonConfig(name="B", key="s", pin=8),
        ButtonConfig(name="C", key="d", pin=9),
        ButtonConfig(name="UP", key="up", pin=22),
        ButtonConfig(name="DOWN", key="down", pin=6),
    ])

    # No touch
    has_touch: bool = False

    # WiFi/Bluetooth via ESP32 module
    has_wifi: bool = True

    # No front RGB LEDs
    num_rgb_leds: int = 0

    # 4 rear lighting zones
    num_rear_zones: int = 4

    # Light sensor (LTR-559 or similar)
    has_light_sensor: bool = True
    has_accelerometer: bool = False

    # Built-in 1000mAh battery
    has_battery: bool = True
    battery_capacity_mah: int = 1000

    # No buzzer
    has_buzzer: bool = False

    # No SD card
    has_sd_card: bool = False

    # RP2350 with 8MB PSRAM
    has_psram: bool = True
