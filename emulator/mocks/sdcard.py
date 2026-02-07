"""Mock implementation of MicroPython's sdcard module.

Provides SD card filesystem access. In the emulator, this maps to a local
directory that simulates the SD card contents.
"""

from pathlib import Path
from emulator import get_state


# Default SD card directory (can be overridden via emulator state)
DEFAULT_SD_PATH = Path("/tmp/presto_sdcard")


class SDCard:
    """Mock SD card interface.

    In MicroPython, this uses SPI to communicate with an SD card.
    In the emulator, we map to a local directory.
    """

    def __init__(self, spi, cs, baudrate=1320000):
        """Initialize SD card.

        Args:
            spi: SPI bus instance
            cs: Chip select pin
            baudrate: SPI baudrate (ignored in emulator)
        """
        self._spi = spi
        self._cs = cs
        self._baudrate = baudrate
        self._mounted = False

        # Get SD card path from emulator state or use default
        state = get_state()
        sd_path = state.get("sdcard_path", DEFAULT_SD_PATH)
        self._path = Path(sd_path)

        # Ensure the directory exists
        self._path.mkdir(parents=True, exist_ok=True)

        if state.get("trace"):
            print(f"[sdcard] Initialized, path={self._path}")

    def readblocks(self, block_num, buf):
        """Read blocks from SD card (low-level, not typically used directly)."""
        pass

    def writeblocks(self, block_num, buf):
        """Write blocks to SD card (low-level, not typically used directly)."""
        pass

    def ioctl(self, op, arg):
        """I/O control operations."""
        if op == 4:  # Get sector count
            return 1024 * 1024  # Fake 512MB card
        elif op == 5:  # Get sector size
            return 512
        return 0

    def get_path(self) -> Path:
        """Get the local filesystem path for this SD card."""
        return self._path
