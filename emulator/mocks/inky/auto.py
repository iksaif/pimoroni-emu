"""Auto-detection mock for Inky displays.

In the emulator, auto-detection returns a mock display based on
the configured device type.
"""

from typing import Optional, Any
from emulator import get_state
from emulator.mocks.inky.inky import Inky
from emulator.mocks.inky.inky_uc8159 import InkyUC8159
from emulator.mocks.inky.inky_ac073tc1a import InkyAC073TC1A


def auto(
    i2c_bus: Any = None,
    ask_user: bool = True,
    verbose: bool = False,
) -> Inky:
    """Auto-detect and return the appropriate Inky display.

    In the emulator, this returns a display based on the configured device.

    Args:
        i2c_bus: I2C bus (ignored in emulator)
        ask_user: Prompt for manual selection if detection fails
        verbose: Print detection info

    Returns:
        Appropriate Inky display instance
    """
    state = get_state()
    device = state.get("device")

    if verbose or state.get("trace"):
        print(f"[inky.auto] Detecting display for device: {device}")

    if device is None:
        # Default to 7-color impression
        if verbose:
            print("[inky.auto] No device configured, defaulting to InkyUC8159")
        return InkyUC8159()

    device_name = getattr(device, "name", "").lower()

    # Match device to appropriate Inky class
    if "spectra" in device_name or "7.3" in device_name or "73" in device_name:
        if verbose:
            print(f"[inky.auto] Detected Spectra 6-color display: {device_name}")
        return InkyAC073TC1A(
            resolution=(device.display_width, device.display_height)
        )
    elif "impression" in device_name or "5.7" in device_name or "4.0" in device_name:
        if verbose:
            print(f"[inky.auto] Detected 7-color Impression display: {device_name}")
        return InkyUC8159(
            resolution=(device.display_width, device.display_height)
        )
    else:
        # Default to base Inky class
        if verbose:
            print(f"[inky.auto] Using base Inky class for: {device_name}")
        return Inky(
            resolution=(device.display_width, device.display_height),
            colour=getattr(device, "colour", "black"),
        )
