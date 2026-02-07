"""Sensor simulation."""

from typing import Tuple
from emulator import get_state
from emulator.devices.base import BaseDevice


class SensorManager:
    """Manages simulated sensor values."""

    def __init__(self, device: BaseDevice):
        self.device = device

        # Light sensor (0-65535)
        self._light_value = 32768  # Middle value

        # Accelerometer (x, y, z in g units, -2 to +2)
        self._accel_x = 0.0
        self._accel_y = 0.0
        self._accel_z = 1.0  # Default: device flat on table

    def set_light(self, value: int):
        """Set light sensor value (0-65535)."""
        self._light_value = max(0, min(65535, value))

        # Update Tufty device if present
        state = get_state()
        tufty = state.get("tufty2350")
        if tufty:
            tufty._set_light(self._light_value)

        if state.get("trace"):
            print(f"[Sensors] Light: {self._light_value}")

    def get_light(self) -> int:
        """Get light sensor value."""
        return self._light_value

    def set_accelerometer(self, x: float, y: float, z: float):
        """Set accelerometer values (in g units)."""
        self._accel_x = max(-2.0, min(2.0, x))
        self._accel_y = max(-2.0, min(2.0, y))
        self._accel_z = max(-2.0, min(2.0, z))

        if get_state().get("trace"):
            print(f"[Sensors] Accel: ({self._accel_x:.2f}, {self._accel_y:.2f}, {self._accel_z:.2f})")

    def get_accelerometer(self) -> Tuple[float, float, float]:
        """Get accelerometer values."""
        return (self._accel_x, self._accel_y, self._accel_z)

    def simulate_tilt_from_mouse(self, dx: int, dy: int, sensitivity: float = 0.01):
        """Simulate accelerometer tilt based on mouse movement."""
        if not self.device.has_accelerometer:
            return

        # Convert mouse delta to tilt
        self._accel_x = max(-2.0, min(2.0, dx * sensitivity))
        self._accel_y = max(-2.0, min(2.0, dy * sensitivity))
        # Z stays roughly 1g (gravity)
        self._accel_z = 1.0 - abs(self._accel_x) * 0.1 - abs(self._accel_y) * 0.1

    def reset_sensors(self):
        """Reset all sensors to default values."""
        self._light_value = 32768
        self._accel_x = 0.0
        self._accel_y = 0.0
        self._accel_z = 1.0
