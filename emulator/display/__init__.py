"""Display renderers for Pimoroni emulator."""

from emulator.display.base import BaseDisplay
from emulator.display.tft import TFTDisplay
from emulator.display.led_matrix import LEDMatrixDisplay
from emulator.display.eink import EInkDisplay


def create_display(device, headless: bool = False) -> BaseDisplay:
    """Create appropriate display renderer for device."""
    if device.display_type == "led_matrix":
        return LEDMatrixDisplay(device, headless=headless)
    elif device.display_type == "eink":
        return EInkDisplay(device, headless=headless)
    else:
        return TFTDisplay(device, headless=headless)
