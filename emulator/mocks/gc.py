"""Mock implementation of MicroPython's gc module."""

import gc as _gc
from emulator import get_state


def collect():
    """Run garbage collection."""
    _gc.collect()
    tracker = get_state().get("memory_tracker")
    if tracker:
        tracker.check_budget()


def enable():
    """Enable automatic garbage collection."""
    _gc.enable()


def disable():
    """Disable automatic garbage collection."""
    _gc.disable()


def isenabled() -> bool:
    """Check if GC is enabled."""
    return _gc.isenabled()


def mem_free() -> int:
    """Return approximate free memory in bytes."""
    tracker = get_state().get("memory_tracker")
    if tracker:
        return tracker.mem_free()
    return 8 * 1024 * 1024  # Fallback: 8MB


def mem_alloc() -> int:
    """Return approximate allocated memory in bytes."""
    tracker = get_state().get("memory_tracker")
    if tracker:
        return tracker.mem_alloc()
    return 512 * 1024  # Fallback


def threshold(amount: int = None) -> int:
    """Get or set GC threshold."""
    if amount is not None:
        _gc.set_threshold(amount)
    thresholds = _gc.get_threshold()
    return thresholds[0] if thresholds else 0
