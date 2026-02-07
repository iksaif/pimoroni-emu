"""Mock implementation of the touch module for Presto.

Provides touch button functionality and touch controller emulation.
"""

from typing import List, Tuple
from emulator import get_state
from emulator.mocks.base import trace_log


class Button:
    """Touch button that tracks touch regions."""

    buttons: List["Button"] = []

    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.pressed = False
        Button.buttons.append(self)

    def is_pressed(self) -> bool:
        """Check if button is currently pressed."""
        return self.pressed

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get button bounds as (x, y, w, h)."""
        return self.x, self.y, self.w, self.h

    @classmethod
    def clear_buttons(cls):
        """Clear all registered buttons."""
        cls.buttons = []


class FT6236:
    """Mock FT6236 capacitive touch controller.

    In the emulator, touch state is set via mouse events.
    """

    STATE_DOWN = 0b00
    STATE_UP = 0b01
    STATE_CONTACT = 0b10
    STATE_NONE = 0b11

    def __init__(self, full_res: bool = False, enable_interrupt: bool = False):
        self.debug = False
        self._scale = 1 if full_res else 2
        self._irq = enable_interrupt

        # Primary touch point
        self.x = 240 if full_res else 120
        self.y = 240 if full_res else 120
        self.state = False

        # Secondary touch point (for multi-touch)
        self.x2 = 240 if full_res else 120
        self.y2 = 240 if full_res else 120
        self.state2 = False

        # Multi-touch distance and angle
        self.distance = 0
        self.angle = 0

        # Register with emulator state
        get_state()["touch_controller"] = self
        trace_log("FT6236", f"Initialized, full_res={full_res}")

    def poll(self):
        """Poll touch state and update buttons.

        In the emulator, this reads the touch state from the emulator state
        (set by mouse events).
        """
        state = get_state()

        # Get touch state from emulator (set by TouchManager)
        touch_data = state.get("touch_state", {})
        self.x = touch_data.get("x", self.x)
        self.y = touch_data.get("y", self.y)
        self.state = touch_data.get("pressed", False)

        # Scale coordinates if needed
        if self._scale != 1:
            self.x = int(self.x / self._scale)
            self.y = int(self.y / self._scale)

        # Update all registered buttons
        for button in Button.buttons:
            if self.state:
                # Check if primary touch is in button bounds
                if (button.x <= self.x <= button.x + button.w and
                    button.y <= self.y <= button.y + button.h):
                    button.pressed = True
                # Check secondary touch
                elif (self.state2 and
                      button.x <= self.x2 <= button.x + button.w and
                      button.y2 <= self.y2 <= button.y + button.h):
                    button.pressed = True
                else:
                    button.pressed = False
            else:
                button.pressed = False

        if self.debug:
            print(f"[FT6236] x={self.x}, y={self.y}, state={self.state}")

    def _set_touch(self, x: int, y: int, pressed: bool):
        """Set touch state (called by emulator)."""
        self.x = x
        self.y = y
        self.state = pressed
