"""Pimoroni Device Emulator.

A desktop emulator for Pimoroni RP2350 devices:
- Tufty 2350 (2.8" TFT badge)
- Blinky 2350 (LED matrix badge)
- Presto (4" touchscreen desktop)

Usage:
    python -m emulator --device tufty apps/tufty/badge.py
    python -m emulator --device presto --headless apps/presto/app.py
"""

__version__ = "0.1.0"

# Global state accessible to mocks
_emulator_state = {
    "device": None,
    "display": None,
    "running": False,
    "headless": False,
    "trace": False,
    "autosave_dir": None,
    "frame_count": 0,
    "memory_tracker": None,
}


def get_state():
    """Get the global emulator state."""
    return _emulator_state


def get_display():
    """Get the current display renderer."""
    return _emulator_state.get("display")


def get_device():
    """Get the current device configuration."""
    return _emulator_state.get("device")
