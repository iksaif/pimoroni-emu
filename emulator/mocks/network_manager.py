"""Mock implementation of Badger2040W's network_manager module.

Provides WiFi management for Badger 2040 W apps.
"""

from emulator.mocks.base import trace_log


class NetworkManager:
    """WiFi network manager for Badger2040W."""

    def __init__(self, country="GB", status_handler=None, error_handler=None):
        self._country = country
        self._status_handler = status_handler
        self._error_handler = error_handler
        self._connected = False
        self._ip = "192.168.1.100"
        self._mode = None

    def isconnected(self):
        return self._connected

    def ifaddress(self):
        return self._ip

    def config(self, key):
        if key == "mac":
            return b'\xaa\xbb\xcc\xdd\xee\xff'
        return ""

    def mode(self):
        return self._mode

    def disconnect(self):
        self._connected = False
        trace_log("network_manager", "Disconnected")

    async def client(self, ssid, psk="", timeout=30):
        """Connect as WiFi client."""
        from emulator.mocks.network import WLAN, STA_IF
        wlan = WLAN(STA_IF)
        wlan.active(True)
        wlan.connect(ssid, psk)

        self._connected = wlan.isconnected()
        self._ip = wlan.ifconfig()[0]
        self._mode = "client"

        if self._status_handler:
            self._status_handler("Connected" if self._connected else "Failed")

        trace_log("network_manager", f"Client connected to {ssid}: {self._ip}")

    async def access_point(self, ssid=None, password=None):
        """Start as access point."""
        self._connected = True
        self._ip = "10.10.1.1"
        self._mode = "ap"
        trace_log("network_manager", f"AP mode: {ssid or 'PimoroniAP'}")

    async def wait(self, mode=None):
        """Wait for connection."""
        pass
