"""RGB LED simulation."""

from typing import List, Tuple
from emulator import get_state
from emulator.devices.base import BaseDevice


class RGBLEDManager:
    """Manages RGB LED simulation."""

    def __init__(self, device: BaseDevice):
        self.device = device
        self._num_leds = device.num_rgb_leds
        self._leds: List[Tuple[int, int, int]] = [(0, 0, 0)] * self._num_leds
        self._brightness = 1.0

    def set_led(self, index: int, r: int, g: int, b: int):
        """Set individual LED color."""
        if 0 <= index < self._num_leds:
            self._leds[index] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )

            if get_state().get("trace"):
                print(f"[RGBLED] LED {index}: ({r}, {g}, {b})")

    def set_all(self, r: int, g: int, b: int):
        """Set all LEDs to same color."""
        for i in range(self._num_leds):
            self._leds[i] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )

    def set_brightness(self, brightness: float):
        """Set global brightness (0.0 to 1.0)."""
        self._brightness = max(0.0, min(1.0, brightness))

    def get_leds(self) -> List[Tuple[int, int, int]]:
        """Get current LED colors with brightness applied."""
        factor = self._brightness
        return [
            (int(r * factor), int(g * factor), int(b * factor))
            for r, g, b in self._leds
        ]

    def clear(self):
        """Turn off all LEDs."""
        self._leds = [(0, 0, 0)] * self._num_leds

    def rainbow(self, offset: float = 0.0):
        """Set LEDs to rainbow pattern."""
        import colorsys

        for i in range(self._num_leds):
            hue = (i / self._num_leds + offset) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self._leds[i] = (int(r * 255), int(g * 255), int(b * 255))

    def update_from_presto(self):
        """Sync LEDs from Presto device if present."""
        state = get_state()
        presto = state.get("presto")

        if presto:
            self._leds = list(presto._leds)
            self._brightness = presto._led_brightness
