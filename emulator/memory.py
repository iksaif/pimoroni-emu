"""Memory tracking for emulated MicroPython heap.

Uses tracemalloc with filename filtering to estimate app memory usage,
then scales CPython sizes to approximate MicroPython equivalents.

Snapshots are cached and only refreshed every SAMPLE_INTERVAL seconds
to avoid the overhead of tracemalloc.take_snapshot() on every call.
"""

import os
import time
import tracemalloc

# How often (in seconds) to take a fresh tracemalloc snapshot.
SAMPLE_INTERVAL = 2.0


class MemoryTracker:
    """Tracks memory allocated by app code using tracemalloc.

    Only counts allocations from the app directory — mock modules
    (picographics, machine, jpegdec, …) correspond to C firmware on
    real hardware and don't consume MicroPython heap.

    CPython objects are larger than MicroPython equivalents (~3x for small
    objects, ~1x for raw buffers). We apply a blended scale factor based
    on the average allocation size.
    """

    def __init__(self, heap_size: int, app_path: str, strict: bool = False):
        self._heap_size = heap_size
        self._app_dir = os.path.dirname(os.path.abspath(app_path))
        self._strict = strict
        self._cached_alloc = 0
        self._cache_time = 0.0

    def start(self):
        """Start tracemalloc. Must be called before app code runs."""
        tracemalloc.start()

    def stop(self):
        """Stop tracemalloc."""
        if tracemalloc.is_tracing():
            tracemalloc.stop()

    def _refresh_cache(self):
        """Take a snapshot and update cached allocation, if stale."""
        now = time.monotonic()
        if now - self._cache_time < SAMPLE_INTERVAL:
            return
        self._cache_time = now
        if not tracemalloc.is_tracing():
            self._cached_alloc = 0
            return
        snapshot = tracemalloc.take_snapshot()
        raw = 0
        for stat in snapshot.statistics("filename"):
            if stat.traceback[0].filename.startswith(self._app_dir):
                raw += stat.size
        scaled = int(raw * self._scale_factor(raw))
        self._cached_alloc = min(scaled, self._heap_size)

    def _scale_factor(self, raw_bytes: int) -> float:
        """CPython-to-MicroPython scale factor.

        Large allocations (buffers) are ~1:1.
        Small object-heavy code inflates ~3x on CPython.
        """
        if raw_bytes <= 10_000:
            return 0.3
        if raw_bytes >= 500_000:
            return 1.0
        t = (raw_bytes - 10_000) / (500_000 - 10_000)
        return 0.3 + t * 0.7

    def mem_alloc(self) -> int:
        """Estimated MicroPython heap bytes allocated."""
        self._refresh_cache()
        return self._cached_alloc

    def mem_free(self) -> int:
        """Estimated MicroPython heap bytes free."""
        return max(0, self._heap_size - self.mem_alloc())

    def check_budget(self):
        """In strict mode, raise MemoryError if budget exceeded."""
        alloc = self.mem_alloc()
        if self._strict and alloc >= self._heap_size:
            raise MemoryError(
                f"Emulated heap exhausted: {alloc} / {self._heap_size} bytes"
            )
