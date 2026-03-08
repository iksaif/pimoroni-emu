"""Auto-detection mock for Inky displays.

In the emulator, auto-detection returns a mock display based on
the configured device type.
"""

from typing import Any

from emulator import get_state
from emulator.mocks.inky.inky import Inky
from emulator.mocks.inky.inky_ac073tc1a import InkyAC073TC1A
from emulator.mocks.inky.inky_spectra6 import InkySpectra6
from emulator.mocks.inky.inky_uc8159 import InkyUC8159

# Match upstream inky.auto DISPLAY_TYPES
DISPLAY_TYPES = [
    "what", "phat", "phatssd1608", "impressions", "7colour",
    "whatssd1683", "impressions73", "spectra13", "spectra73",
    "spectra40", "phatjd79661", "whatjd79668",
]
DISPLAY_COLORS = ["red", "black", "yellow", "red/yellow"]

# UC8159 (ACeP) resolutions — older 7-color panels
_UC8159_RESOLUTIONS = {(600, 448), (640, 400)}


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
    width = getattr(device, "display_width", 0)
    height = getattr(device, "display_height", 0)
    eink_colors = getattr(device, "eink_colors", 2)

    # Match device to appropriate Inky class
    if eink_colors >= 7:
        # 7-color display — pick driver by resolution
        if (width, height) in _UC8159_RESOLUTIONS:
            # UC8159 (ACeP): 5.7" (600x448) and 4.0" (640x400)
            if verbose:
                print(f"[inky.auto] Detected UC8159 7-color display: {device_name}")
            return InkyUC8159(resolution=(width, height))
        else:
            # AC073TC1A: 7.3" (800x480), 7 colors including orange
            if verbose:
                print(f"[inky.auto] Detected AC073TC1A 7-color display: {device_name}")
            return InkyAC073TC1A(resolution=(width, height))

    elif eink_colors == 6:
        # Spectra 6-color display (E673, E640, EL133UF1)
        if verbose:
            print(f"[inky.auto] Detected Spectra 6-color display: {device_name}")
        return InkySpectra6(resolution=(width, height))

    else:
        # B/W or B/W + accent (pHAT, wHAT, JD79661, JD79668)
        colour = "black"
        if "red" in device_name:
            colour = "red"
        elif "yellow" in device_name:
            colour = "yellow"

        if verbose:
            print(f"[inky.auto] Detected {eink_colors}-color display: {device_name}")
        return Inky(
            resolution=(width, height),
            colour=colour,
        )
