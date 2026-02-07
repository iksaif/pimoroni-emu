"""Mock battery state for the emulator.

Provides a controllable battery level via the sensor panel slider.
"""

from emulator import get_state


class Battery:
    """Mock battery with controllable voltage and charging state."""

    def __init__(self):
        self._voltage = 3.7  # Default: ~60% charge
        self._charging = False
        self._usb_connected = True
        # Register in emulator state for sensor panel and ADC
        get_state()["battery"] = self

    def _set_values(self, voltage=None, charging=None, usb_connected=None):
        """Set mock values (called by sensor panel slider)."""
        if voltage is not None:
            self._voltage = voltage
        if charging is not None:
            self._charging = bool(charging)
        if usb_connected is not None:
            self._usb_connected = usb_connected

    def get_level(self):
        """Get battery level as percentage (0-100).

        Uses the same formula as the real Pimoroni badgeware firmware.
        """
        v = self._voltage
        return min(100, max(0, round(123 - (123 / pow((1 + pow((v / 3.2), 80)), 0.165)))))


# Singleton instance created on import
_battery = None


def init_battery():
    """Initialize the battery mock."""
    global _battery
    if _battery is None:
        _battery = Battery()
    return _battery
