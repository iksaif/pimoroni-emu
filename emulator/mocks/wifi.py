"""Stub `wifi` module for the emulator.

Pimoroni's badgeware firmware exposes a small `wifi` convenience
module wrapping the underlying network stack. Apps in
vendor/tufty2350/firmware/apps/{clock,weather,...} and the equivalent
Badger apps `import wifi` and call connect()/tick() to wait for
association before fetching data. In the emulator we just claim
"connected" so those apps proceed past the gate.

Use --real-network on the emulator CLI if you want actual HTTP to
work; that's wired through the existing urequests / network mocks
and doesn't need any wifi setup.
"""

from emulator import get_state


def _get_wlan():
    """Return the singleton WLAN STA interface, creating it if needed."""
    import network as _net  # noqa: PLC0415 — lazy to avoid circular import at load time
    return _net.WLAN(_net.STA_IF)


def connect(ssid=None, password=None):
    """Pretend to start connecting. Marks the WLAN mock as connected."""
    wlan = _get_wlan()
    wlan.active(True)
    wlan._connected = True
    wlan._ip = "192.168.1.100"
    wlan._gateway = "192.168.1.1"
    wlan._dns = "8.8.8.8"
    if ssid:
        wlan._ssid = ssid
    return True


def tick():
    """Return True once connected. Ensures the WLAN mock reports connected."""
    wlan = _get_wlan()
    if not wlan._connected:
        connect()
    return True


def is_connected():
    return _get_wlan()._connected


def disconnect():
    wlan = _get_wlan()
    wlan._connected = False


def status():
    return "connected"


def ip():
    return _get_wlan()._ip
