"""Mock implementation of MICS6814 3-in-1 gas sensor breakout."""

from emulator.mocks.base import I2CSensorMock


class BreakoutMICS6814(I2CSensorMock):
    """MICS6814 3-channel gas sensor (reducing, NH3, oxidising)."""

    _component_name = "MICS6814"
    _default_address = 0x19

    def __init__(self, i2c, address=0x19):
        super().__init__(i2c, address)

    def read_all(self):
        """Read all three gas channels. Returns (reducing, nh3, oxidising)."""
        return (0.5, 0.3, 0.4)

    def read_reducing(self):
        return 0.5

    def read_nh3(self):
        return 0.3

    def read_oxidising(self):
        return 0.4

    def set_heater(self, on):
        pass

    def set_brightness(self, brightness):
        pass

    def set_led(self, r, g, b):
        pass
