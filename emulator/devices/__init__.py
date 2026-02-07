"""Device configurations for Pimoroni emulator."""

from emulator.devices.base import BaseDevice
from emulator.devices.tufty2350 import Tufty2350Device
from emulator.devices.blinky2350 import Blinky2350Device
from emulator.devices.presto import PrestoDevice
from emulator.devices.badger2350 import Badger2350Device
from emulator.devices.inky_frame import (
    InkyFrame73Device,
    InkyFrame58Device,
    InkyFrame40Device,
)
from emulator.devices.inky_impression import (
    InkyImpression73Device,
    InkyImpression57Device,
    InkyImpression40Device,
    InkyImpression133Device,
)


DEVICES = {
    "tufty": Tufty2350Device,
    "tufty2350": Tufty2350Device,
    "blinky": Blinky2350Device,
    "blinky2350": Blinky2350Device,
    "presto": PrestoDevice,
    "badger": Badger2350Device,
    "badger2040": Badger2350Device,  # Same display dimensions
    "badger2350": Badger2350Device,
    # Inky Frame (MicroPython/PicoGraphics on RP2040/RP2350)
    "inky_frame": InkyFrame73Device,
    "inky_frame_7": InkyFrame73Device,
    "inky_frame_73": InkyFrame73Device,
    "inky_frame_5": InkyFrame58Device,
    "inky_frame_58": InkyFrame58Device,
    "inky_frame_4": InkyFrame40Device,
    "inky_frame_40": InkyFrame40Device,
    # Inky Impression (Python/inky library on Raspberry Pi)
    "impression": InkyImpression57Device,
    "impression_73": InkyImpression73Device,
    "impression_57": InkyImpression57Device,
    "impression_40": InkyImpression40Device,
    "impression_133": InkyImpression133Device,
    "inky_impression": InkyImpression57Device,
    "inky_impression_73": InkyImpression73Device,
    "inky_impression_57": InkyImpression57Device,
    "inky_impression_40": InkyImpression40Device,
    "inky_impression_133": InkyImpression133Device,
}


def get_device(name: str) -> BaseDevice:
    """Get device instance by name."""
    name = name.lower()
    if name not in DEVICES:
        available = ", ".join(DEVICES.keys())
        raise ValueError(f"Unknown device '{name}'. Available: {available}")
    return DEVICES[name]()


def list_devices() -> list:
    """List available device names."""
    return list(DEVICES.keys())
