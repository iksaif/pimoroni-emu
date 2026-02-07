"""Example test for Tufty badge app."""

import pytest
from pathlib import Path
import sys

# Add emulator to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from emulator.testing import DeviceTest


class TestTuftyBadge(DeviceTest):
    """Test the Tufty badge application."""

    device = "tufty"
    app = "apps/tufty/hello_badge.py"

    def test_initial_display(self):
        """Test that badge displays correctly on startup."""
        # Run a few frames to let app initialize
        self.run_frames(5)

        # Save screenshot for manual verification
        self.screenshot("tests/output/tufty_initial.png")

    def test_button_changes_color(self):
        """Test that pressing buttons changes background color."""
        self.run_frames(5)

        # Press button A (should change to red)
        self.click_button("A")
        self.run_frames(3)
        self.screenshot("tests/output/tufty_red.png")

        # Press button B (should change to green)
        self.click_button("B")
        self.run_frames(3)
        self.screenshot("tests/output/tufty_green.png")

        # Press button C (should change to blue)
        self.click_button("C")
        self.run_frames(3)
        self.screenshot("tests/output/tufty_blue.png")


class TestPrestoTouch(DeviceTest):
    """Test the Presto touch demo."""

    device = "presto"
    app = "apps/presto/touch_demo.py"

    def test_initial_display(self):
        """Test initial display with buttons."""
        self.run_frames(5)
        self.screenshot("tests/output/presto_initial.png")

    def test_touch_button(self):
        """Test touching a button."""
        self.run_frames(5)

        # Touch the red button area (top-left)
        self.touch(100, 100)
        self.run_frames(3)
        self.screenshot("tests/output/presto_touch_red.png")
        self.release_touch()


class TestBlinkyScroll(DeviceTest):
    """Test the Blinky scrolling text."""

    device = "blinky"
    app = "apps/blinky/scrolling_text.py"

    def test_scrolling(self):
        """Test that text scrolls across the display."""
        # Capture several frames to see scrolling
        self.run_frames(10)
        self.screenshot("tests/output/blinky_frame1.png")

        self.run_frames(10)
        self.screenshot("tests/output/blinky_frame2.png")

        self.run_frames(10)
        self.screenshot("tests/output/blinky_frame3.png")


# Run with: pytest tests/test_tufty_badge.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
