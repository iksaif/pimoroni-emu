"""Mock implementation of MicroPython's machine module."""

import time as _time
from typing import Callable, Optional, Any
from emulator import get_state


# Constants
PWRON_RESET = 1
HARD_RESET = 2
WDT_RESET = 3
DEEPSLEEP_RESET = 4
SOFT_RESET = 5


class Pin:
    """Mock GPIO Pin."""

    IN = 0
    OUT = 1
    OPEN_DRAIN = 2
    ALT = 3

    PULL_UP = 1
    PULL_DOWN = 2

    IRQ_RISING = 1
    IRQ_FALLING = 2
    IRQ_LOW_LEVEL = 4
    IRQ_HIGH_LEVEL = 8

    _pins: dict[int, "Pin"] = {}

    def __init__(
        self,
        id: int,
        mode: int = -1,
        pull: int = -1,
        value: Optional[int] = None,
        *,
        alt: int = -1
    ):
        self.id = id
        self._mode = mode if mode != -1 else Pin.IN
        self._pull = pull
        if value is not None:
            self._value = value
        elif pull == Pin.PULL_UP:
            self._value = 1  # PULL_UP defaults high
        else:
            self._value = 0
        self._irq_handler: Optional[Callable] = None
        self._irq_trigger = 0
        Pin._pins[id] = self

    def init(self, mode: int = -1, pull: int = -1, value: Optional[int] = None):
        if mode != -1:
            self._mode = mode
        if pull != -1:
            self._pull = pull
        if value is not None:
            self._value = value

    def value(self, x: Optional[int] = None) -> Optional[int]:
        if x is None:
            # VBUS_DETECT (pin 24): read USB power state from battery mock
            if self.id == 24:
                battery = get_state().get("battery")
                if battery:
                    return 1 if battery._usb_connected else 0
            return self._value
        self._value = 1 if x else 0
        return None

    def __call__(self, x: Optional[int] = None) -> Optional[int]:
        return self.value(x)

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def toggle(self):
        self._value = 1 - self._value

    def irq(
        self,
        handler: Optional[Callable] = None,
        trigger: int = IRQ_RISING | IRQ_FALLING,
        *,
        hard: bool = False
    ):
        self._irq_handler = handler
        self._irq_trigger = trigger

    def _trigger_irq(self, new_value: int):
        """Called by emulator to simulate interrupt with edge detection."""
        old_value = self._value
        self._value = new_value
        if self._irq_handler:
            fire = False
            if old_value == 0 and new_value == 1:
                fire = bool(self._irq_trigger & Pin.IRQ_RISING)
            elif old_value == 1 and new_value == 0:
                fire = bool(self._irq_trigger & Pin.IRQ_FALLING)
            if fire:
                self._irq_handler(self)

    @classmethod
    def get_pin(cls, id: int) -> Optional["Pin"]:
        return cls._pins.get(id)


class _PinBoardMeta(type):
    """Metaclass to make Pin.board.__dict__ work correctly."""

    _pin_defs = {
        # Blinky 2350 buttons
        "BUTTON_A": (7, Pin.IN, Pin.PULL_UP),
        "BUTTON_B": (8, Pin.IN, Pin.PULL_UP),
        "BUTTON_C": (9, Pin.IN, Pin.PULL_UP),
        "BUTTON_UP": (22, Pin.IN, Pin.PULL_UP),
        "BUTTON_DOWN": (6, Pin.IN, Pin.PULL_UP),
        "BUTTON_HOME": (10, Pin.IN, Pin.PULL_UP),
        "BUTTON_INT": (0, Pin.IN, Pin.PULL_UP),

        # Power management pins
        "VBUS_DETECT": (24, Pin.IN, -1),
        "CHARGE_STAT": (25, Pin.IN, -1),
        "VBAT_SENSE": (26, Pin.IN, -1),
        "SENSE_1V1": (27, Pin.IN, -1),
        "POWER_EN": (28, Pin.OUT, -1),
        "RTC_ALARM": (29, Pin.IN, -1),

        # Case lights (PWM)
        "CL0": (16, Pin.OUT, -1),
        "CL1": (17, Pin.OUT, -1),
        "CL2": (18, Pin.OUT, -1),
        "CL3": (19, Pin.OUT, -1),
    }

    _pins = {}

    def __getattr__(cls, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in cls._pin_defs:
            if name not in cls._pins:
                pin_id, mode, pull = cls._pin_defs[name]
                cls._pins[name] = Pin(pin_id, mode, pull)
            return cls._pins[name]
        raise AttributeError(f"Pin.board has no attribute '{name}'")


class _PinBoard(metaclass=_PinBoardMeta):
    """Named pin constants for board-specific pins.

    Pins are created lazily on first access.
    """
    pass


# Populate __dict__ with pin objects for `locals().update(Pin.board.__dict__)`
for _name in _PinBoardMeta._pin_defs:
    setattr(_PinBoard, _name, getattr(_PinBoard, _name))

# Attach board to Pin class
Pin.board = _PinBoard


class PWM:
    """Mock PWM output."""

    def __init__(self, pin: Pin, *, freq: int = 0, duty_u16: int = 0, duty_ns: int = 0):
        self._pin = pin
        self._freq = freq
        self._duty_u16 = duty_u16
        self._duty_ns = duty_ns

    def freq(self, value: Optional[int] = None) -> Optional[int]:
        if value is None:
            return self._freq
        self._freq = value
        return None

    def duty_u16(self, value: Optional[int] = None) -> Optional[int]:
        if value is None:
            return self._duty_u16
        self._duty_u16 = value
        return None

    def duty_ns(self, value: Optional[int] = None) -> Optional[int]:
        if value is None:
            return self._duty_ns
        self._duty_ns = value
        return None

    def deinit(self):
        pass


class I2C:
    """Mock I2C bus."""

    def __init__(self, id: int = 0, *, scl: Optional[Pin] = None, sda: Optional[Pin] = None, freq: int = 400000):
        self.id = id
        self._scl = scl
        self._sda = sda
        self._freq = freq
        self._devices: dict[int, bytes] = {}

    def scan(self) -> list[int]:
        """Return list of detected device addresses."""
        return list(self._devices.keys())

    def readfrom(self, addr: int, nbytes: int, stop: bool = True) -> bytes:
        return self._devices.get(addr, b"\x00" * nbytes)[:nbytes]

    def readfrom_into(self, addr: int, buf: bytearray, stop: bool = True):
        data = self.readfrom(addr, len(buf), stop)
        buf[:len(data)] = data

    def writeto(self, addr: int, buf: bytes, stop: bool = True) -> int:
        if get_state().get("trace"):
            print(f"[I2C] Write to 0x{addr:02x}: {buf.hex()}")
        return len(buf)

    def readfrom_mem(self, addr: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        return b"\x00" * nbytes

    def readfrom_mem_into(self, addr: int, memaddr: int, buf: bytearray, *, addrsize: int = 8):
        pass

    def writeto_mem(self, addr: int, memaddr: int, buf: bytes, *, addrsize: int = 8):
        if get_state().get("trace"):
            print(f"[I2C] Write to 0x{addr:02x} mem 0x{memaddr:02x}: {buf.hex()}")


class SPI:
    """Mock SPI bus."""

    MSB = 0
    LSB = 1

    def __init__(
        self,
        id: int,
        baudrate: int = 1000000,
        *,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = MSB,
        sck: Optional[Pin] = None,
        mosi: Optional[Pin] = None,
        miso: Optional[Pin] = None
    ):
        self.id = id
        self._baudrate = baudrate
        self._polarity = polarity
        self._phase = phase
        self._bits = bits
        self._firstbit = firstbit

    def init(self, baudrate: int = 1000000, **kwargs):
        self._baudrate = baudrate

    def deinit(self):
        pass

    def read(self, nbytes: int, write: int = 0x00) -> bytes:
        return bytes([write] * nbytes)

    def readinto(self, buf: bytearray, write: int = 0x00):
        for i in range(len(buf)):
            buf[i] = write

    def write(self, buf: bytes):
        if get_state().get("trace"):
            print(f"[SPI] Write: {buf[:32].hex()}{'...' if len(buf) > 32 else ''}")

    def write_readinto(self, write_buf: bytes, read_buf: bytearray):
        for i in range(min(len(write_buf), len(read_buf))):
            read_buf[i] = 0


class Timer:
    """Mock hardware timer."""

    ONE_SHOT = 0
    PERIODIC = 1

    _timers: list["Timer"] = []

    def __init__(self, id: int = -1):
        self.id = id
        self._mode = Timer.PERIODIC
        self._period = 0
        self._callback: Optional[Callable] = None
        self._running = False
        Timer._timers.append(self)

    def init(
        self,
        *,
        mode: int = PERIODIC,
        period: int = -1,
        freq: float = -1,
        callback: Optional[Callable] = None
    ):
        self._mode = mode
        if freq > 0:
            self._period = int(1000 / freq)
        elif period > 0:
            self._period = period
        self._callback = callback
        self._running = True
        self._last_tick = _time.time() * 1000

    def deinit(self):
        self._running = False
        self._callback = None

    def _tick(self, current_ms: float):
        """Called by emulator main loop."""
        if not self._running or not self._callback:
            return
        if current_ms - self._last_tick >= self._period:
            self._callback(self)
            self._last_tick = current_ms
            if self._mode == Timer.ONE_SHOT:
                self._running = False


class ADC:
    """Mock ADC input."""

    # Internal temperature sensor channel
    CORE_TEMP = 4

    def __init__(self, pin):
        # Accept integer channel (e.g. ADC(4) for temp sensor) or Pin object
        if isinstance(pin, int):
            self._channel = pin
            self._pin = None
        else:
            self._channel = None
            self._pin = pin
        self._value = 0

    def read_u16(self) -> int:
        """Read 16-bit ADC value (0-65535)."""
        if self._channel == 4:
            # Internal temperature sensor: return value for ~22.5C
            # Formula: T = 27 - (V - 0.706) / 0.001721, V = reading * 3.3 / 65535
            # For 22.5C: V = 0.706 + (27 - 22.5) * 0.001721 = 0.71374
            # reading = 0.71374 / 3.3 * 65535 = 14177
            return 14177

        pin_id = self._channel or (self._pin.id if self._pin else None)
        battery = get_state().get("battery")

        # VBAT_SENSE (pin 26): battery through 2:1 external divider
        if pin_id == 26 and battery:
            # ADC sees voltage/2, reading = (voltage/2) / 3.3 * 65535
            return int((battery._voltage / 2) / 3.3 * 65535)

        # SENSE_1V1 (pin 27): internal 1.1V reference
        if pin_id == 27:
            return int(1.1 / 3.3 * 65535)

        # VSYS (pin 29): system input voltage through internal 3:1 divider
        # On Pico W / Inky Frame, apps read ADC(Pin(29)) to get battery voltage.
        # The RP2040/RP2350 has an internal 3:1 divider on this pin.
        # Voltage = reading * 3.3 / 65535 * 3
        if pin_id == 29 and battery:
            return int((battery._voltage / 3) / 3.3 * 65535)

        return self._value

    def _set_value(self, value: int):
        """Set mock value (for testing)."""
        self._value = max(0, min(65535, value))


class RTC:
    """Mock Real-Time Clock."""

    def __init__(self):
        pass

    def datetime(self, dt: tuple = None):
        """Get or set datetime.

        Format: (year, month, day, weekday, hour, minute, second, subsecond)
        """
        if dt is not None:
            # Setting time - we can't actually set system time
            return
        # Return current time
        import datetime
        now = datetime.datetime.now()
        # weekday: 0=Monday
        return (now.year, now.month, now.day, now.weekday(),
                now.hour, now.minute, now.second, 0)

    def init(self, datetime: tuple):
        """Initialize RTC with datetime."""
        pass

    def deinit(self):
        """Deinitialize RTC."""
        pass


class mem32:
    """Mock memory access."""

    _memory: dict[int, int] = {}

    def __getitem__(self, addr: int) -> int:
        return mem32._memory.get(addr, 0)

    def __setitem__(self, addr: int, value: int):
        mem32._memory[addr] = value & 0xFFFFFFFF


mem32 = mem32()


class _MachineResetError(SystemExit):
    """Raised to signal the emulator to restart the app (simulates reboot)."""
    pass


def reset():
    """Reset the device.

    In emulator, restarts the app script (simulates a reboot).
    """
    print("[machine] Reset requested - restarting app")
    raise _MachineResetError(0)


def soft_reset():
    """Soft reset the device."""
    print("[machine] Soft reset requested - restarting app")
    raise _MachineResetError(0)


def reset_cause() -> int:
    """Return reset cause."""
    return PWRON_RESET


def freq(hz: Optional[int] = None) -> int:
    """Get or set CPU frequency."""
    if hz is not None:
        return hz
    return 150_000_000  # RP2350 default


def unique_id() -> bytes:
    """Return unique device ID."""
    return b"\x00\x01\x02\x03\x04\x05\x06\x07"


def idle():
    """Wait for interrupt."""
    _time.sleep(0.001)


def lightsleep(time_ms: Optional[int] = None):
    """Enter light sleep."""
    if time_ms:
        _time.sleep(time_ms / 1000)


def deepsleep(time_ms: Optional[int] = None):
    """Enter deep sleep."""
    if time_ms:
        _time.sleep(time_ms / 1000)
