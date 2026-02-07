"""Mock implementation of LSM6DS3 accelerometer/gyroscope sensor."""

from emulator.mocks.base import I2CSensorMock

# ODR (Output Data Rate) constants
NORMAL_MODE_104HZ = 104
NORMAL_MODE_208HZ = 208
NORMAL_MODE_416HZ = 416
HIGH_PERFORMANCE_MODE_833HZ = 833
HIGH_PERFORMANCE_MODE_1660HZ = 1660


class LSM6DS3(I2CSensorMock):
    """LSM6DS3 6-axis accelerometer/gyroscope."""

    _component_name = "LSM6DS3"
    _default_address = 0x6A

    def __init__(self, i2c, address=0x6A, mode=NORMAL_MODE_104HZ, gyro_odr=None, accel_odr=None):
        super().__init__(i2c, address)
        self._mode = mode
        # Default mock values (neutral orientation)
        self._accel = (0.0, 0.0, 1.0)  # x, y, z in g
        self._gyro = (0.0, 0.0, 0.0)  # x, y, z in degrees/sec
        # Register with emulator state for sensor panel
        self._register("lsm6ds3")

    def get_readings(self):
        """Get accelerometer and gyroscope readings.

        Returns: (ax, ay, az, gx, gy, gz)
        """
        return self._accel + self._gyro

    def get_accel(self):
        """Get accelerometer readings (ax, ay, az) in g."""
        return self._accel

    def get_gyro(self):
        """Get gyroscope readings (gx, gy, gz) in degrees/sec."""
        return self._gyro

    @property
    def acceleration(self):
        """Get accelerometer readings (ax, ay, az) in g."""
        return self._accel

    @property
    def gyro(self):
        """Get gyroscope readings (gx, gy, gz) in degrees/sec."""
        return self._gyro

    def _set_values(self, accel=None, gyro=None):
        """Set mock sensor values for testing."""
        if accel is not None:
            self._accel = tuple(accel)
        if gyro is not None:
            self._gyro = tuple(gyro)
