"""Base classes and helpers for mock implementations."""

from emulator import get_state


def trace_log(component: str, message: str):
    """Log a trace message if trace mode is enabled.

    Args:
        component: Name of the component (e.g., "BME280", "PicoGraphics")
        message: The message to log
    """
    if get_state().get("trace"):
        print(f"[{component}] {message}")


class MockDevice:
    """Base class for mock devices with tracing support."""

    _component_name = "MockDevice"

    def _trace(self, message: str):
        """Log a trace message for this component."""
        trace_log(self._component_name, message)

    def _register(self, key: str):
        """Register this device in the emulator state.

        Args:
            key: The key to register under in get_state()
        """
        get_state()[key] = self


class I2CSensorMock(MockDevice):
    """Base class for I2C sensor mocks.

    Provides common initialization for I2C-based sensors including
    address storage and trace logging.
    """

    _default_address = 0x00

    def __init__(self, i2c, address: int = None):
        """Initialize I2C sensor mock.

        Args:
            i2c: I2C bus instance (stored but not used in mock)
            address: I2C device address
        """
        self._i2c = i2c
        self._address = address if address is not None else self._default_address
        self._trace(f"Initialized at 0x{self._address:02x}")
