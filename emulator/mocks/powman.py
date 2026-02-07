"""Mock implementation of the powman module for power management.

This module provides power management functions for RP2350 devices.
"""

from emulator import get_state


# Wake reason constants
WAKE_UNKNOWN = 255
WAKE_BUTTON_A = 1
WAKE_BUTTON_B = 2
WAKE_BUTTON_C = 3
WAKE_BUTTON_UP = 4
WAKE_BUTTON_DOWN = 5
WAKE_BUTTON_HOME = 6
WAKE_RTC = 10


def get_wake_reason():
    """Get the reason the device woke from sleep."""
    # In emulator, default to WAKE_UNKNOWN (reset)
    return WAKE_UNKNOWN


def get_wake_buttons():
    """Get which buttons can wake the device."""
    return [WAKE_BUTTON_A, WAKE_BUTTON_B, WAKE_BUTTON_C,
            WAKE_BUTTON_UP, WAKE_BUTTON_DOWN]


def sleep():
    """Put the device to sleep."""
    state = get_state()
    if state.get("trace"):
        print("[powman] Sleep requested")
    # In emulator, just stop running
    state["running"] = False


def _test_psram_cs():
    """Test PSRAM chip select (for hardware tests)."""
    return True
