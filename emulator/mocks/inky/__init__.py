"""Mock implementation of Pimoroni's inky library for Raspberry Pi.

This provides compatibility with the inky Python library used by
Inky Impression and other Raspberry Pi-based e-ink displays.
"""

from emulator.mocks.inky.inky import Inky, InkyMock
from emulator.mocks.inky.inky_uc8159 import InkyUC8159
from emulator.mocks.inky.inky_ac073tc1a import InkyAC073TC1A

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

__all__ = [
    "Inky",
    "InkyMock",
    "InkyUC8159",
    "InkyAC073TC1A",
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
