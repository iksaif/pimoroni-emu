"""Mock implementation of Presto's ezwifi module.

Provides simplified WiFi connection for Presto apps.
"""

from emulator.mocks.base import trace_log


class LogLevel:
    INFO = 0
    WARNING = 1
    ERROR = 2


class EzWiFi:
    """Simplified WiFi manager for Presto."""

    def __init__(self):
        self._connected = False
        self._ip = "192.168.1.100"
        self._callbacks = {}

    def on(self, event, callback):
        """Register event callback (connected, failed, info, warning, error)."""
        self._callbacks[event] = callback

    async def connect(self, ssid=None, password=None, timeout=30):
        """Connect to WiFi (simulated)."""
        if ssid is None:
            try:
                from secrets import WIFI_SSID, WIFI_PASSWORD
                ssid = WIFI_SSID
                password = WIFI_PASSWORD
            except ImportError:
                trace_log("ezwifi", "No secrets.py found, simulating connection")
                ssid = "emulator"
                password = ""

        trace_log("ezwifi", f"Connecting to {ssid}")

        from emulator.mocks.network import WLAN, STA_IF
        wlan = WLAN(STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password or "")

        self._connected = wlan.isconnected()
        self._ip = wlan.ifconfig()[0]

        if self._connected and "connected" in self._callbacks:
            self._callbacks["connected"](self._ip)

        return self._connected

    def error(self, msg):
        """Log an error."""
        trace_log("ezwifi", f"Error: {msg}")
        if "error" in self._callbacks:
            self._callbacks["error"](msg)

    def isconnected(self):
        return self._connected

    def ipv4(self):
        return self._ip

    def ipv6(self):
        return "::1"


def connect(ssid=None, password=None, timeout=30):
    """Synchronous WiFi connect helper."""
    import asyncio
    wifi = EzWiFi()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    loop.run_until_complete(wifi.connect(ssid, password, timeout))
    return wifi
