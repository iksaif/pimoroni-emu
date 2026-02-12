"""Mock implementation of MicroPython's uasyncio module.

Wraps CPython's asyncio with MicroPython compatibility:
- get_event_loop() auto-creates a loop in any thread (MicroPython behaviour)
"""

import asyncio as _asyncio

# Re-export everything from asyncio
from asyncio import *  # noqa: F401,F403


def get_event_loop():
    """Get the running event loop, creating one if needed.

    MicroPython's uasyncio always has a loop available. CPython raises
    RuntimeError in non-main threads, so we create one automatically.
    """
    try:
        return _asyncio.get_event_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        return loop
