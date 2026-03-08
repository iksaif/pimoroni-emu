"""Mock implementation of Pimoroni's inky library for Raspberry Pi.

This provides compatibility with the inky Python library used by
Inky Impression and other Raspberry Pi-based e-ink displays.

Mock class mapping to upstream drivers:
  InkyPHAT, InkyPHAT_SSD1608    → Inky base (B/W + accent, 212x104 / 250x122)
  InkyWHAT, InkyWHAT_SSD1683    → Inky base (B/W + accent, 400x300)
  InkyJD79661                    → Inky base (4-color, 250x122)
  InkyJD79668                    → Inky base (4-color, 400x300)
  InkyUC8159                     → InkyUC8159 (ACeP 7-color, 600x448 / 640x400)
  InkyAC073TC1A                  → InkyAC073TC1A (7-color, 800x480)
  InkyE673                       → InkySpectra6 (Spectra 6-color, 800x480)
  InkyE640                       → InkySpectra6 (Spectra 6-color, 600x400)
  InkyEL133UF1                   → InkySpectra6 (Spectra 6-color, 1600x1200)
"""

from emulator.mocks.inky.inky import Inky, InkyMock
from emulator.mocks.inky.inky_ac073tc1a import InkyAC073TC1A
from emulator.mocks.inky.inky_spectra6 import InkySpectra6
from emulator.mocks.inky.inky_uc8159 import InkyUC8159

# Color constants
WHITE = 0
BLACK = 1
RED = 2
YELLOW = 2  # Same as RED on some displays
GREEN = 3
BLUE = 4
ORANGE = 5
CLEAN = 6

# Display types
PHAT = "phat"
WHAT = "what"
IMPRESSION = "impression"
IMPRESSION_73 = "impression_73"
IMPRESSION_57 = "impression_57"
IMPRESSION_40 = "impression_40"
SPECTRA_13 = "spectra_13"

# --- Aliases for upstream driver classes ---
# Legacy pHAT/wHAT — same interface as base Inky, different default resolutions


class InkyPHAT(Inky):
    """Inky pHAT (original, 212x104)."""
    WIDTH = 212
    HEIGHT = 104


class InkyPHAT_SSD1608(Inky):
    """Inky pHAT SSD1608 (250x122)."""
    WIDTH = 250
    HEIGHT = 122


class InkyWHAT(Inky):
    """Inky wHAT (400x300)."""
    WIDTH = 400
    HEIGHT = 300


class InkyWHAT_SSD1683(Inky):
    """Inky wHAT SSD1683 (400x300)."""
    WIDTH = 400
    HEIGHT = 300


class InkyJD79661(Inky):
    """Inky pHAT JD79661 (250x122, 4-color)."""
    WIDTH = 250
    HEIGHT = 122


class InkyJD79668(Inky):
    """Inky wHAT JD79668 (400x300, 4-color)."""
    WIDTH = 400
    HEIGHT = 300


# Spectra 6-color variants — 6 colors, different index order from AC073TC1A


class InkyE673(InkySpectra6):
    """Inky Impression 7.3" E673 variant (800x480, Spectra 6)."""
    WIDTH = 800
    HEIGHT = 480


class InkyE640(InkySpectra6):
    """Inky Impression 4.0" Spectra E640 (600x400, Spectra 6)."""
    WIDTH = 600
    HEIGHT = 400


class InkyEL133UF1(InkySpectra6):
    """Inky Impression 13.3" EL133UF1 (1600x1200, Spectra 6)."""
    WIDTH = 1600
    HEIGHT = 1200


__all__ = [
    "Inky",
    "InkyMock",
    "InkyUC8159",
    "InkyAC073TC1A",
    "InkySpectra6",
    "InkyPHAT",
    "InkyPHAT_SSD1608",
    "InkyWHAT",
    "InkyWHAT_SSD1683",
    "InkyJD79661",
    "InkyJD79668",
    "InkyE673",
    "InkyE640",
    "InkyEL133UF1",
    "WHITE",
    "BLACK",
    "RED",
    "YELLOW",
    "GREEN",
    "BLUE",
    "ORANGE",
    "CLEAN",
    "PHAT",
    "WHAT",
    "IMPRESSION",
]
