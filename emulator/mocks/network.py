"""Mock implementation of MicroPython's network module."""

from typing import Optional, Tuple
from emulator import get_state


# Interface types
STA_IF = 0
AP_IF = 1

# Status codes
STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_WRONG_PASSWORD = 2
STAT_NO_AP_FOUND = 3
STAT_CONNECT_FAIL = 4
STAT_GOT_IP = 5

# Singleton instances for each interface (like real MicroPython)
_interfaces = {}


class WLAN:
    """WiFi interface."""

    def __new__(cls, interface_id: int = STA_IF):
        """Return existing interface or create new one (singleton per interface)."""
        if interface_id in _interfaces:
            return _interfaces[interface_id]
        instance = super().__new__(cls)
        _interfaces[interface_id] = instance
        return instance

    def __init__(self, interface_id: int = STA_IF):
        # Only initialize if not already initialized
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self._interface_id = interface_id
        self._active = False
        self._connected = False
        self._ssid = ""
        self._ip = "0.0.0.0"
        self._subnet = "255.255.255.0"
        self._gateway = "0.0.0.0"
        self._dns = "0.0.0.0"
        self._mac = b"\xaa\xbb\xcc\xdd\xee\xff"
        self._hostname = "pimoroni"

        # Register with emulator
        state = get_state()
        state["wlan"] = self

    def active(self, is_active: Optional[bool] = None) -> bool:
        """Get or set interface active state."""
        if is_active is not None:
            self._active = is_active
            if get_state().get("trace"):
                print(f"[WLAN] Active: {is_active}")
        return self._active

    def connect(self, ssid: str, password: str = "", **kwargs):
        """Connect to WiFi network."""
        self._ssid = ssid
        if get_state().get("trace"):
            print(f"[WLAN] Connecting to '{ssid}'...")

        # Simulate successful connection
        self._connected = True
        self._ip = "192.168.1.100"
        self._gateway = "192.168.1.1"
        self._dns = "8.8.8.8"

        if get_state().get("trace"):
            print(f"[WLAN] Connected! IP: {self._ip}")

    def disconnect(self):
        """Disconnect from WiFi."""
        self._connected = False
        self._ip = "0.0.0.0"
        if get_state().get("trace"):
            print("[WLAN] Disconnected")

    def isconnected(self) -> bool:
        """Check if connected to WiFi."""
        return self._connected

    def status(self, param: Optional[str] = None):
        """Get connection status."""
        if param == "rssi":
            return -50  # Good signal
        if self._connected:
            return STAT_GOT_IP
        return STAT_IDLE

    def ifconfig(self, config: Optional[Tuple] = None) -> Tuple[str, str, str, str]:
        """Get or set IP configuration."""
        if config is not None:
            self._ip, self._subnet, self._gateway, self._dns = config
        return (self._ip, self._subnet, self._gateway, self._dns)

    def config(self, **kwargs):
        """Configure interface parameters."""
        for key, value in kwargs.items():
            if key == "hostname":
                self._hostname = value
            elif key == "mac":
                self._mac = value
            if get_state().get("trace"):
                print(f"[WLAN] Config {key}={value}")

    def scan(self) -> list:
        """Scan for available networks."""
        # Return fake networks for testing
        return [
            (b"TestNetwork1", b"\x00\x11\x22\x33\x44\x55", 6, -50, 3, False),
            (b"TestNetwork2", b"\xaa\xbb\xcc\xdd\xee\xff", 11, -70, 4, True),
        ]


def hostname(name: Optional[str] = None) -> str:
    """Get or set hostname."""
    state = get_state()
    wlan = state.get("wlan")
    if wlan:
        if name is not None:
            wlan._hostname = name
        return wlan._hostname
    return "pimoroni"


def country(code: Optional[str] = None) -> str:
    """Get or set country code."""
    return "GB"
