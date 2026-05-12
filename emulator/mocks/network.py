"""Mock implementation of MicroPython's network module."""

import random
import re
import subprocess
import sys
import time
from typing import Optional, Tuple

from emulator import get_state

# Centre RSSI per simulated network profile (dBm). Real WiFi RSSI typically
# sits between -30 (excellent) and -90 (unusable).
_RSSI_PROFILES = {
    "real": -52,
    "host": -52,  # fallback when host RSSI can't be read
    "healthy": -48,
    "degraded": -72,
    "down": -90,
}

# Cache for host RSSI lookups (subprocess calls are slow).
_host_rssi_cache: dict = {"value": None, "ts": 0.0}


def _read_host_rssi() -> Optional[int]:
    """Read the host machine's WiFi RSSI in dBm. Best-effort, returns None on failure.

    The macOS `system_profiler` call is slow (3-10s), so results are cached
    for 30 seconds.
    """
    now = time.time()
    if now - _host_rssi_cache["ts"] < 30.0 and _host_rssi_cache["value"] is not None:
        return _host_rssi_cache["value"]

    rssi: Optional[int] = None
    # NOTE: `platform.system()` is overridden by `_patch_os_uname()` to report
    # as 'rp2', so we use `sys.platform` (unaffected) instead.
    if sys.platform == "darwin":
        # `airport -I` is deprecated but still ships on macOS < 15 and runs
        # without sudo. Fast (<100ms) so try it first.
        airport = (
            "/System/Library/PrivateFrameworks/Apple80211.framework"
            "/Versions/Current/Resources/airport"
        )
        try:
            out = subprocess.run(
                [airport, "-I"], capture_output=True, text=True, timeout=2
            ).stdout
            m = re.search(r"agrCtlRSSI:\s*(-?\d+)", out)
            if m:
                rssi = int(m.group(1))
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            pass
        if rssi is None:
            # macOS 15+ removed `airport`; fall back to the slow system_profiler.
            try:
                out = subprocess.run(
                    ["system_profiler", "SPAirPortDataType"],
                    capture_output=True, text=True, timeout=15,
                ).stdout
                m = re.search(r"Signal\s*/\s*Noise:\s*(-?\d+)\s*dBm", out)
                if m:
                    rssi = int(m.group(1))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
    elif sys.platform.startswith("linux"):
        for cmd in (["iw", "dev"], ["iwconfig"]):
            try:
                out = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=2
                ).stdout
                m = re.search(r"signal[:\s]+(-?\d+)\s*dBm", out, re.IGNORECASE)
                if m:
                    rssi = int(m.group(1))
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    _host_rssi_cache["value"] = rssi
    _host_rssi_cache["ts"] = now
    return rssi

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
        state = get_state()

        if state.get("no_wifi"):
            if state.get("trace"):
                print(f"[WLAN] Connection to '{ssid}' failed (--no-wifi)")
            self._connected = False
            self._ip = "0.0.0.0"
            raise OSError("WiFi connection failed (--no-wifi)")

        if state.get("trace"):
            print(f"[WLAN] Connecting to '{ssid}'...")

        # Simulate successful connection
        self._connected = True
        self._ip = "192.168.1.100"
        self._gateway = "192.168.1.1"
        self._dns = "8.8.8.8"

        if state.get("trace"):
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
            profile = get_state().get("network_profile", "real")
            if profile == "host":
                real = _read_host_rssi()
                if real is not None:
                    return real
            centre = _RSSI_PROFILES.get(profile, -52)
            # Slow sinusoidal drift + small jitter, so monitor apps see a
            # plausibly live signal rather than a frozen value.
            t = time.time()
            drift = 3.0 * ((t % 30) / 30 - 0.5)  # ±1.5 dBm over 30s
            jitter = random.uniform(-1.0, 1.0)
            return int(round(centre + drift + jitter))
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
