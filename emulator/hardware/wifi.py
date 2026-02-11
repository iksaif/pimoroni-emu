"""WiFi simulation."""

from typing import Optional
from emulator import get_state
from emulator.devices.base import BaseDevice


class WiFiManager:
    """Manages WiFi simulation (network requests pass through to host)."""

    def __init__(self, device: BaseDevice):
        self.device = device

    def get_status(self) -> dict:
        """Get WiFi status."""
        state = get_state()
        wlan = state.get("wlan")

        if not wlan:
            return {
                "active": False,
                "connected": False,
                "ssid": "",
                "ip": "0.0.0.0",
            }

        return {
            "active": wlan._active,
            "connected": wlan._connected,
            "ssid": wlan._ssid,
            "ip": wlan._ip,
        }

    def simulate_connect(self, ssid: str, ip: str = "192.168.1.100"):
        """Simulate successful WiFi connection."""
        state = get_state()
        wlan = state.get("wlan")

        if wlan:
            wlan._ssid = ssid
            wlan._connected = True
            wlan._ip = ip

        if state.get("trace"):
            print(f"[WiFi] Simulated connection to '{ssid}' with IP {ip}")

    def simulate_disconnect(self):
        """Simulate WiFi disconnection."""
        state = get_state()
        wlan = state.get("wlan")

        if wlan:
            wlan._connected = False
            wlan._ip = "0.0.0.0"

        if state.get("trace"):
            print("[WiFi] Simulated disconnection")

    def simulate_poor_signal(self, rssi: int = -80):
        """Simulate poor WiFi signal."""
        # This would affect request latency in a more advanced simulation
        if get_state().get("trace"):
            print(f"[WiFi] Simulated poor signal: {rssi} dBm")
