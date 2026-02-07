"""Mock implementation of MSA301 accelerometer breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutMSA301(I2CSensorMock):
    """MSA301 3-axis accelerometer."""

    _component_name = "MSA301"
    _default_address = 0x26

    # Part IDs
    PART_ID = 0x13

    def __init__(self, i2c, address=0x26):
        super().__init__(i2c, address)
        self._x = 0.0
        self._y = 0.0
        self._z = 1.0  # 1g on Z (gravity)

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y

    def get_z(self):
        return self._z

    def read(self):
        """Read accelerometer. Returns (x, y, z) in g."""
        return (self._x, self._y, self._z)

    def get_orientation(self):
        """Get orientation based on accel data."""
        return 0  # Portrait up

    def set_power_mode(self, mode): pass
    def set_range(self, range_g): pass
    def set_resolution(self, bits): pass
