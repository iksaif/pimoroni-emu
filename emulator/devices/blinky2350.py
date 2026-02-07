"""Blinky 2350 device configuration."""

from dataclasses import dataclass, field
from typing import List
from emulator.devices.base import BaseDevice, ButtonConfig


@dataclass
class Blinky2350Device(BaseDevice):
    """Blinky 2350 - 3.6" white LED matrix badge."""

    name: str = "Blinky 2350"
    description: str = "3.6\" white LED matrix badge (872 LEDs)"

    # Display: 39x26 LED matrix (from blinky.c)
    display_width: int = 39
    display_height: int = 26
    display_type: str = "led_matrix"
    display_scale: int = 12  # Larger scale for visibility
    color_depth: int = 8  # 8-bit brightness per LED
    is_color: bool = False  # White-only LEDs

    # Library type for badgeware API
    library_type: str = "badgeware"

    # Buttons (5 front buttons, same as Tufty)
    buttons: List[ButtonConfig] = field(default_factory=lambda: [
        ButtonConfig(name="A", key="a", pin=7),
        ButtonConfig(name="B", key="s", pin=8),
        ButtonConfig(name="C", key="d", pin=9),
        ButtonConfig(name="UP", key="up", pin=22),
        ButtonConfig(name="DOWN", key="down", pin=6),
    ])

    # No touch
    has_touch: bool = False

    # WiFi/Bluetooth
    has_wifi: bool = True

    # No front RGB LEDs
    num_rgb_leds: int = 0

    # 4 rear lighting zones
    num_rear_zones: int = 4

    # No sensors exposed
    has_light_sensor: bool = False
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
