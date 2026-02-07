"""Mock implementation of PSRAM (Pseudo-Static RAM) module."""

from emulator import get_state, get_device

# Default PSRAM size (8MB as per RP2350 devices)
PSRAM_SIZE = 8 * 1024 * 1024

_psram_used = 0


def available():
    """Check if PSRAM is available."""
    device = get_device()
    if device:
        return getattr(device, 'has_psram', False)
    return True


def size():
    """Get PSRAM size in bytes."""
    if not available():
        return 0
    return PSRAM_SIZE


def allocate(nbytes):
    """Allocate memory from PSRAM."""
    global _psram_used
    if get_state().get("trace"):
        print(f"[PSRAM] Allocated {nbytes} bytes")
    _psram_used += nbytes
    return bytearray(nbytes)


def free(buf):
    """Free PSRAM allocation."""
    global _psram_used
    if get_state().get("trace"):
        print(f"[PSRAM] Freed buffer ({len(buf)} bytes)")
    _psram_used = max(0, _psram_used - len(buf))


def used():
    """Get used PSRAM size."""
    return _psram_used


def free_size():
    """Get free PSRAM size."""
    if not available():
        return 0
    return max(0, PSRAM_SIZE - _psram_used)
