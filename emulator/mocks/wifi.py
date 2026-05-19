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


def connect(ssid=None, password=None):
    """Pretend to start connecting. Always succeeds."""
    return True


def tick():
    """Return True once connected (we report connected immediately)."""
    return True


def is_connected():
    return True


def disconnect():
    pass


def status():
    return "connected"


def ip():
    return "127.0.0.1"
