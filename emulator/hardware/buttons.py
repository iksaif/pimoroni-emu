"""Button input simulation."""

from typing import Dict, Optional, Set
from emulator import get_state
from emulator.devices.base import BaseDevice, ButtonConfig


class ButtonManager:
    """Manages keyboard to button mapping."""

    def __init__(self, device: BaseDevice):
        self.device = device
        self._pressed_keys: Set[str] = set()

        # Create Button instances for each configured button
        from emulator.mocks.pimoroni import Button
        for btn_config in device.buttons:
            Button(btn_config.pin)

    def handle_key_down(self, key: str):
        """Handle keyboard key press."""
        key = key.lower()

        if key in self._pressed_keys:
            return  # Already pressed

        self._pressed_keys.add(key)

        # Find matching button
        btn_config = self.device.get_button_by_key(key)
        if btn_config:
            self._press_button(btn_config.pin)

    def handle_key_up(self, key: str):
        """Handle keyboard key release."""
        key = key.lower()

        if key not in self._pressed_keys:
            return

        self._pressed_keys.discard(key)

        # Find matching button
        btn_config = self.device.get_button_by_key(key)
        if btn_config:
            self._release_button(btn_config.pin)

    def _press_button(self, pin: int):
        """Press a button by pin number."""
        state = get_state()
        buttons = state.get("buttons", {})
        btn = buttons.get(pin)
        if btn:
            btn._press()
            # Buttons are active-low with PULL_UP: pressed = value 0 (falling edge)
            from emulator.mocks.machine import Pin
            pin_obj = Pin.get_pin(pin)
            if pin_obj:
                pin_obj._trigger_irq(0)

    def _release_button(self, pin: int):
        """Release a button by pin number."""
        state = get_state()
        buttons = state.get("buttons", {})
        btn = buttons.get(pin)
        if btn:
            btn._release()
            # Buttons are active-low with PULL_UP: released = value 1 (rising edge)
            from emulator.mocks.machine import Pin
            pin_obj = Pin.get_pin(pin)
            if pin_obj:
                pin_obj._trigger_irq(1)

    def is_pressed(self, pin: int) -> bool:
        """Check if button is pressed by pin."""
        state = get_state()
        buttons = state.get("buttons", {})
        btn = buttons.get(pin)
        return btn._pressed if btn else False

    def get_pressed_buttons(self) -> list:
        """Get list of currently pressed button names."""
        pressed = []
        for btn_config in self.device.buttons:
            if self.is_pressed(btn_config.pin):
                pressed.append(btn_config.name)
        return pressed

    @staticmethod
    def pygame_key_to_name(pygame_key: int) -> Optional[str]:
        """Convert pygame key code to key name."""
        # Lazy import pygame
        try:
            import pygame
        except ImportError:
            return None

        key_map = {
            pygame.K_a: "a",
            pygame.K_b: "b",
            pygame.K_c: "c",
            pygame.K_d: "d",
            pygame.K_s: "s",
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_SPACE: "space",
            pygame.K_RETURN: "return",
            pygame.K_ESCAPE: "escape",
            pygame.K_r: "r",
            pygame.K_q: "q",
            pygame.K_z: "z",
            pygame.K_x: "x",
            pygame.K_v: "v",
            pygame.K_MINUS: "-",
            pygame.K_EQUALS: "=",
        }

        return key_map.get(pygame_key)
