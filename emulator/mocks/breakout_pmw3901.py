"""Mock implementation of PMW3901 optical flow sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutPMW3901(I2CSensorMock):
    """PMW3901 optical flow sensor."""

    _component_name = "PMW3901"
    _default_address = 0x00  # SPI, not I2C

    def __init__(self, *args, **kwargs):
        self._dx = 0
        self._dy = 0

    def get_motion(self, timeout=5):
        """Get motion deltas. Returns (dx, dy)."""
        return (self._dx, self._dy)

    def set_rotation(self, degrees=0):
        pass

    def set_orientation(self, invert_x=True, invert_y=True, swap_xy=True):
        pass

    def frame_capture(self, frame, timeout=10):
        """Capture a raw frame (35x35 pixels)."""
        for i in range(len(frame)):
            frame[i] = 128
