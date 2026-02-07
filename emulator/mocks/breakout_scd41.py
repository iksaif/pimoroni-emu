"""Mock implementation of SCD41 CO2/temperature/humidity sensor.

Note: SCD41 uses module-level functions, not a class.
"""

from emulator.mocks.base import trace_log
from emulator import get_state

_co2 = 420
_temperature = 22.5
_humidity = 45.0
_started = False


def init(i2c):
    """Initialize the SCD41 sensor."""
    trace_log("SCD41", f"Initialized on I2C")
    get_state()["scd41"] = True


def start():
    """Start periodic measurements."""
    global _started
    _started = True
    trace_log("SCD41", "Started measurements")


def stop():
    """Stop periodic measurements."""
    global _started
    _started = False


def ready():
    """Check if measurement data is ready."""
    return _started


def measure():
    """Read CO2, temperature, humidity. Returns (co2_ppm, temp_c, humidity_%)."""
    return (_co2, _temperature, _humidity)
