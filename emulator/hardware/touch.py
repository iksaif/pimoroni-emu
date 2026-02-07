"""Touchscreen simulation."""

from typing import Optional, Tuple
from emulator import get_state
from emulator.devices.base import BaseDevice


class TouchManager:
    """Manages mouse to touch mapping for touchscreen devices."""

    def __init__(self, device: BaseDevice):
        self.device = device
        self._touch_x = 0
        self._touch_y = 0
        self._touch_pressed = False

    def handle_mouse_down(self, window_x: int, window_y: int):
        """Handle mouse button press."""
        if not self.device.has_touch:
            return

        # Convert window coordinates to display coordinates
        touch_pos = self._window_to_display(window_x, window_y)
        if touch_pos:
            self._touch_x, self._touch_y = touch_pos
            self._touch_pressed = True
            self._update_device_touch()

            if get_state().get("trace"):
                print(f"[Touch] Press at ({self._touch_x}, {self._touch_y})")

    def handle_mouse_up(self, window_x: int, window_y: int):
        """Handle mouse button release."""
        if not self.device.has_touch:
            return

        self._touch_pressed = False
        self._update_device_touch()

        if get_state().get("trace"):
            print("[Touch] Release")

    def handle_mouse_move(self, window_x: int, window_y: int):
        """Handle mouse movement (for drag)."""
        if not self.device.has_touch or not self._touch_pressed:
            return

        touch_pos = self._window_to_display(window_x, window_y)
        if touch_pos:
            self._touch_x, self._touch_y = touch_pos
            self._update_device_touch()

    def _window_to_display(self, win_x: int, win_y: int) -> Optional[Tuple[int, int]]:
        """Convert window coordinates to display coordinates."""
        disp_rect = self.device.get_display_rect()
        x, y, w, h = disp_rect

        # Check if within display bounds
        if not (x <= win_x < x + w and y <= win_y < y + h):
            return None

        # Convert to display coordinates
        display_x = (win_x - x) * self.device.display_width // w
        display_y = (win_y - y) * self.device.display_height // h

        # Clamp to display bounds
        display_x = max(0, min(self.device.display_width - 1, display_x))
        display_y = max(0, min(self.device.display_height - 1, display_y))

        return (display_x, display_y)

    def _update_device_touch(self):
        """Update touch state in device mock."""
        state = get_state()

        # Store touch state for FT6236.poll() to read
        state["touch_state"] = {
            "x": self._touch_x,
            "y": self._touch_y,
            "pressed": self._touch_pressed
        }

    def get_touch(self) -> Tuple[int, int, bool]:
        """Get current touch state."""
        return (self._touch_x, self._touch_y, self._touch_pressed)

    def is_touched(self) -> bool:
        """Check if screen is currently touched."""
        return self._touch_pressed
