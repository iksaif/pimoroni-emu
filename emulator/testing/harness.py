"""Test harness for device testing."""

import sys
import threading
import time
import runpy
from pathlib import Path
from typing import Optional
from unittest import TestCase

from emulator import get_state, _emulator_state
from emulator.devices import get_device
from emulator.display import create_display
from emulator.hardware.buttons import ButtonManager
from emulator.hardware.touch import TouchManager
from emulator.hardware.sensors import SensorManager
from emulator.mocks import install_mocks
from emulator.testing.capture import screenshot
from emulator.testing.compare import assert_display_matches


class DeviceTest(TestCase):
    """Base class for device tests.

    Example usage:

        class TestMyBadge(DeviceTest):
            device = "tufty"
            app = "apps/tufty/badge.py"

            def test_displays_name(self):
                self.run_frames(10)
                self.assert_display_matches("expected/badge.png")

            def test_button_press(self):
                self.press_button("A")
                self.run_frames(5)
                self.screenshot("after_button.png")
    """

    # Override in subclass
    device: str = "presto"
    app: Optional[str] = None

    # Test state
    _device_instance = None
    _display = None
    _button_manager = None
    _touch_manager = None
    _sensor_manager = None
    _app_thread = None

    @classmethod
    def setUpClass(cls):
        """Set up device and display for all tests."""
        # Get device
        cls._device_instance = get_device(cls.device)

        # Set up emulator state
        _emulator_state["device"] = cls._device_instance
        _emulator_state["running"] = True
        _emulator_state["headless"] = True
        _emulator_state["trace"] = False

        # Install mocks
        install_mocks()

        # Create display (headless)
        cls._display = create_display(cls._device_instance, headless=True)
        _emulator_state["display"] = cls._display
        cls._display.init()

        # Set up hardware managers
        cls._button_manager = ButtonManager(cls._device_instance)
        cls._touch_manager = TouchManager(cls._device_instance)
        cls._sensor_manager = SensorManager(cls._device_instance)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        _emulator_state["running"] = False
        if cls._display:
            cls._display.close()

    def setUp(self):
        """Set up before each test."""
        # Reset frame count
        _emulator_state["frame_count"] = 0

        # Start app if specified
        if self.app:
            self._start_app()

    def tearDown(self):
        """Clean up after each test."""
        self._stop_app()

    def _start_app(self):
        """Start the app in a background thread."""
        if not self.app:
            return

        app_path = Path(self.app)
        if not app_path.exists():
            self.fail(f"App not found: {app_path}")

        _emulator_state["running"] = True

        def run_app():
            try:
                app_dir = str(app_path.parent.absolute())
                if app_dir not in sys.path:
                    sys.path.insert(0, app_dir)
                runpy.run_path(str(app_path), run_name="__main__")
            except Exception as e:
                if _emulator_state["running"]:
                    print(f"App error: {e}")

        self._app_thread = threading.Thread(target=run_app, daemon=True)
        self._app_thread.start()

        # Give app time to initialize
        time.sleep(0.1)

    def _stop_app(self):
        """Stop the running app."""
        _emulator_state["running"] = False
        if self._app_thread:
            self._app_thread.join(timeout=1.0)
            self._app_thread = None

    def run_frames(self, count: int, timeout: float = 5.0):
        """Run the app for N frames.

        Args:
            count: Number of frames to run
            timeout: Maximum time to wait
        """
        start_frame = get_state().get("frame_count", 0)
        target_frame = start_frame + count
        start_time = time.time()

        while get_state().get("frame_count", 0) < target_frame:
            if time.time() - start_time > timeout:
                actual = get_state().get("frame_count", 0) - start_frame
                self.fail(f"Timeout waiting for frames. Got {actual}/{count}")
            time.sleep(0.01)

    def press_button(self, name: str):
        """Press a button by name (A, B, C, UP, DOWN)."""
        name = name.lower()
        if self._button_manager:
            self._button_manager.handle_key_down(name)

    def release_button(self, name: str):
        """Release a button by name."""
        name = name.lower()
        if self._button_manager:
            self._button_manager.handle_key_up(name)

    def click_button(self, name: str, duration: float = 0.1):
        """Press and release a button."""
        self.press_button(name)
        time.sleep(duration)
        self.release_button(name)

    def touch(self, x: int, y: int):
        """Simulate touch at coordinates."""
        if self._touch_manager:
            # Convert display coords to window coords
            disp_rect = self._device_instance.get_display_rect()
            win_x = disp_rect[0] + x
            win_y = disp_rect[1] + y
            self._touch_manager.handle_mouse_down(win_x, win_y)

    def release_touch(self):
        """Release touch."""
        if self._touch_manager:
            self._touch_manager.handle_mouse_up(0, 0)

    def set_light_sensor(self, value: int):
        """Set light sensor value (0-65535)."""
        if self._sensor_manager:
            self._sensor_manager.set_light(value)

    def screenshot(self, filename: str) -> bool:
        """Save current display to file."""
        return screenshot(filename)

    def assert_display_matches(
        self,
        expected_path: str,
        threshold: float = 0.99,
        save_diff: Optional[str] = None,
    ):
        """Assert display matches expected image."""
        assert_display_matches(expected_path, threshold, save_diff)
