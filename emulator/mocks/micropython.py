"""Mock implementation of MicroPython's micropython module."""

from typing import Callable, Optional


def const(value):
    """Declare a constant (no-op in CPython, optimization hint in MicroPython)."""
    return value


def opt_level(level: Optional[int] = None) -> int:
    """Get or set optimization level."""
    return 0


def mem_info(verbose: bool = False):
    """Print memory information."""
    from emulator import get_state
    tracker = get_state().get("memory_tracker")
    if tracker:
        used = tracker.mem_alloc()
        free = tracker.mem_free()
        total = used + free
    else:
        total, used, free = 8388608, 524288, 7864320
    print("Memory info:")
    print(f"  stack: 4096 bytes")
    print(f"  GC: total={total}, used={used}, free={free}")
    if verbose:
        print("  No detailed GC blocks in emulator")


def qstr_info(verbose: bool = False):
    """Print qstr (interned string) information."""
    print("qstr info: n_pool=1, n_qstr=100, n_str_data_bytes=2048")


def stack_use() -> int:
    """Return current stack usage in bytes."""
    return 1024


def heap_lock():
    """Lock the heap (prevent allocation)."""
    pass


def heap_unlock():
    """Unlock the heap."""
    pass


def kbd_intr(chr: int):
    """Set character for keyboard interrupt."""
    pass


def schedule(func: Callable, arg):
    """Schedule a function to run soon."""
    # In the emulator, just call immediately
    func(arg)


class RingIO:
    """Ring buffer for inter-thread communication."""

    def __init__(self, size: int):
        self._buffer = bytearray(size)
        self._read_pos = 0
        self._write_pos = 0
        self._size = size

    def any(self) -> int:
        return (self._write_pos - self._read_pos) % self._size

    def read(self, n: int = -1) -> bytes:
        available = self.any()
        if n < 0 or n > available:
            n = available
        result = bytearray(n)
        for i in range(n):
            result[i] = self._buffer[self._read_pos]
            self._read_pos = (self._read_pos + 1) % self._size
        return bytes(result)

    def readline(self) -> bytes:
        result = bytearray()
        while self.any() > 0:
            c = self._buffer[self._read_pos]
            self._read_pos = (self._read_pos + 1) % self._size
            result.append(c)
            if c == ord('\n'):
                break
        return bytes(result)

    def write(self, data: bytes) -> int:
        written = 0
        for byte in data:
            next_pos = (self._write_pos + 1) % self._size
            if next_pos != self._read_pos:
                self._buffer[self._write_pos] = byte
                self._write_pos = next_pos
                written += 1
        return written
