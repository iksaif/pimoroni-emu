"""Mock implementation of MicroPython's rp2 module (RP2040/RP2350 hardware)."""

from emulator.mocks.base import trace_log


def country(code: str = ""):
    """Set or get the wireless country code."""
    trace_log("rp2", f"country({code!r})")
