"""Memory tracking for emulated MicroPython heap.

Uses tracemalloc with filename filtering to estimate app memory usage,
then scales CPython sizes to approximate MicroPython equivalents.
"""

import os
import tracemalloc


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

    def start(self):
        """Start tracemalloc. Must be called before app code runs."""
        tracemalloc.start()

    def stop(self):
        """Stop tracemalloc."""
        if tracemalloc.is_tracing():
            tracemalloc.stop()

    def get_traced_bytes(self) -> int:
        """Sum tracemalloc allocations from app code only."""
        if not tracemalloc.is_tracing():
            return 0
        snapshot = tracemalloc.take_snapshot()
        total = 0
        for stat in snapshot.statistics("filename"):
            if self._should_count(stat.traceback[0].filename):
                total += stat.size
        return total

    def _should_count(self, filename: str) -> bool:
        """True for app directory only (mocks = C firmware, not heap)."""
        return filename.startswith(self._app_dir)

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
        raw = self.get_traced_bytes()
        scaled = int(raw * self._scale_factor(raw))
        return min(scaled, self._heap_size)

    def mem_free(self) -> int:
        """Estimated MicroPython heap bytes free."""
        return max(0, self._heap_size - self.mem_alloc())

    def check_budget(self):
        """In strict mode, raise MemoryError if budget exceeded."""
        if self._strict and self.mem_alloc() >= self._heap_size:
            raise MemoryError(
                f"Emulated heap exhausted: {self.mem_alloc()} / {self._heap_size} bytes"
            )
