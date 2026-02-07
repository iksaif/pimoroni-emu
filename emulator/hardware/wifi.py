"""WiFi simulation."""

from typing import Optional
from emulator import get_state
from emulator.devices.base import BaseDevice


class WiFiManager:
    """Manages WiFi simulation and optional real network access."""

    def __init__(self, device: BaseDevice, use_real_network: bool = False):
        self.device = device
        self._use_real_network = use_real_network

        if use_real_network:
            get_state()["real_network"] = True

    def set_real_network(self, enabled: bool):
        """Enable or disable real network access."""
        self._use_real_network = enabled
        get_state()["real_network"] = enabled

        if get_state().get("trace"):
            print(f"[WiFi] Real network: {enabled}")

    def is_real_network(self) -> bool:
        """Check if using real network."""
        return self._use_real_network

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
