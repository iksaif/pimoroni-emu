"""Mock implementation of MicroPython's time module.

This module provides MicroPython-specific time functions while also
passing through standard Python time functions for compatibility.
"""

import time as _time

# Pass through standard Python time functions that other libraries need
monotonic = _time.monotonic
monotonic_ns = _time.monotonic_ns
perf_counter = _time.perf_counter
perf_counter_ns = _time.perf_counter_ns
process_time = _time.process_time
process_time_ns = _time.process_time_ns
strftime = _time.strftime
strptime = _time.strptime
struct_time = _time.struct_time
timezone = _time.timezone
altzone = getattr(_time, 'altzone', 0)
daylight = _time.daylight
tzname = _time.tzname
clock_gettime = getattr(_time, 'clock_gettime', None)
clock_gettime_ns = getattr(_time, 'clock_gettime_ns', None)
get_clock_info = _time.get_clock_info
CLOCK_MONOTONIC = getattr(_time, 'CLOCK_MONOTONIC', None)
CLOCK_REALTIME = getattr(_time, 'CLOCK_REALTIME', None)


def sleep(seconds: float):
    """Sleep for given number of seconds."""
    _time.sleep(seconds)


def sleep_ms(ms: int):
    """Sleep for given number of milliseconds."""
    _time.sleep(ms / 1000)


def sleep_us(us: int):
    """Sleep for given number of microseconds."""
    _time.sleep(us / 1_000_000)


_start_time = _time.time()


def ticks_ms() -> int:
    """Return millisecond counter (wraps at 2^30)."""
    return int((_time.time() - _start_time) * 1000) & 0x3FFFFFFF


def ticks_us() -> int:
    """Return microsecond counter (wraps at 2^30)."""
    return int((_time.time() - _start_time) * 1_000_000) & 0x3FFFFFFF


def ticks_cpu() -> int:
    """Return CPU ticks (high resolution)."""
    return int((_time.time() - _start_time) * 150_000_000) & 0x3FFFFFFF


def ticks_add(ticks: int, delta: int) -> int:
    """Add delta to ticks value."""
    return (ticks + delta) & 0x3FFFFFFF


def ticks_diff(ticks1: int, ticks2: int) -> int:
    """Compute difference between ticks values."""
    diff = (ticks1 - ticks2) & 0x3FFFFFFF
    if diff >= 0x20000000:
        diff -= 0x40000000
    return diff


def time() -> int:
    """Return seconds since epoch."""
    return int(_time.time())


def time_ns() -> int:
    """Return nanoseconds since epoch."""
    return int(_time.time() * 1_000_000_000)


def localtime(secs: int = None) -> tuple:
    """Convert seconds to local time tuple."""
    if secs is None:
        secs = int(_time.time())
    t = _time.localtime(secs)
    # MicroPython format: (year, month, mday, hour, minute, second, weekday, yearday)
    return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday, t.tm_yday)


def gmtime(secs: int = None) -> tuple:
    """Convert seconds to UTC time tuple."""
    if secs is None:
        secs = int(_time.time())
    t = _time.gmtime(secs)
    return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday, t.tm_yday)


def mktime(t: tuple) -> int:
    """Convert time tuple to seconds since epoch."""
    # t = (year, month, mday, hour, minute, second, weekday, yearday)
    import calendar
    return calendar.timegm((t[0], t[1], t[2], t[3], t[4], t[5], 0, 0, 0))
