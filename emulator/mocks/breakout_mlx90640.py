"""Mock implementation of MLX90640 thermal camera breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutMLX90640(I2CSensorMock):
    """MLX90640 32x24 thermal camera."""

    _component_name = "MLX90640"
    _default_address = 0x33

    def __init__(self, i2c, address=0x33):
        super().__init__(i2c, address)
        self._ambient = 22.5

    def setup(self, fps=2):
        pass

    def get_frame(self):
        """Get thermal frame (768 floats = 32x24 grid)."""
        return [self._ambient + 0.1 * i % 5 for i in range(768)]

    def get_ambient(self):
        return self._ambient
