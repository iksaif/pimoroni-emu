"""Mock implementation of MicroPython's ntptime module.

Provides NTP time synchronization.
"""

import time as _time
from emulator import get_state


# Default NTP server
host = "pool.ntp.org"


def settime():
    """Set the RTC time from an NTP server.

    In the emulator, this is a no-op since we use system time.
    """
    state = get_state()
    if state.get("trace"):
        print(f"[ntptime] settime() called (using system time)")


def time() -> int:
    """Get time from NTP server.

    Returns Unix timestamp.
    """
    return int(_time.time())
