"""Regression tests for the --hardware path on Raspberry Pi e-ink HATs.

These don't need a real HAT — they stand in a fake `inky` package and
assert that the emulator wires render() → set_image()/show() on whatever
real-inky's `auto()` returns.

The third test specifically reproduces the main.py initialisation
ordering and would have caught the bug where install_inky_mocks()
overwrote sys.modules["inky.*"] before init_hardware ran, causing
real-inky's deferred driver import to resolve to our mock.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

from emulator import _emulator_state
from emulator.devices import get_device
from emulator.display.eink import EInkDisplay


@pytest.fixture(autouse=True)
def _isolate_emulator_state():
    """Snapshot+restore shared state and sys.modules['inky.*']."""
    saved_state = dict(_emulator_state)
    saved_inky = {k: v for k, v in sys.modules.items() if k == "inky" or k.startswith("inky.")}
    _emulator_state.clear()
    for k in list(sys.modules):
        if k == "inky" or k.startswith("inky."):
            del sys.modules[k]
    yield
    _emulator_state.clear()
    _emulator_state.update(saved_state)
    for k in list(sys.modules):
        if k == "inky" or k.startswith("inky."):
            del sys.modules[k]
    sys.modules.update(saved_inky)


def _make_display():
    device = get_device("inky_impression_73")
    _emulator_state["device"] = device
    _emulator_state["headless"] = True
    display = EInkDisplay(device, headless=True)
    _emulator_state["display"] = display
    display.init()
    return display


def _blank_buffer(width=800, height=480):
    return [[0xFFFFFF] * width for _ in range(height)]


def test_headless_render_pushes_to_hardware_when_hw_device_set():
    """The render() headless branch must call set_image + show on _hw_device."""
    display = _make_display()
    hw = MagicMock(width=800, height=480, BLACK=0)
    display._hw_device = hw

    display.render(_blank_buffer())

    assert hw.set_image.called, "set_image was not called"
    assert hw.show.called, "show() was not called — panel won't refresh"


def test_init_hardware_stores_auto_result_in_hw_device():
    """init_hardware must call real_inky.auto() and stash its return."""
    fake_hw = MagicMock(width=800, height=480, BLACK=0)
    fake_real_inky = MagicMock()
    fake_real_inky.auto.return_value = fake_hw
    _emulator_state["real_inky"] = fake_real_inky

    display = _make_display()
    display.init_hardware()

    assert fake_real_inky.auto.called, "real_inky.auto() was not called"
    assert display._hw_device is fake_hw, "_hw_device wasn't stored from auto()"


def test_install_inky_mocks_then_init_hardware_keeps_real_driver():
    """install_inky_mocks must not shadow real inky's deferred driver import.

    Real upstream inky.auto() resolves the panel driver via a runtime
    `from inky.inky_ac073tc1a import Inky` (or similar). If our mocks
    are installed in sys.modules first, that import returns *our* mock
    class and the real HAT never sees a frame — even though
    `_hw_device` appears to be set.

    This test stands in a tiny fake of the real inky package with that
    exact deferred-import pattern, then runs the same sequence main.py
    does: stash real_inky → install mocks → init_hardware. It asserts
    that the resulting _hw_device is from the *real* package, not the
    mock.
    """
    # ── Build a minimal "real inky" package with deferred driver import ──
    real_pkg = types.ModuleType("inky")
    real_drv_mod = types.ModuleType("inky.inky_ac073tc1a")

    class RealDriver:
        width = 800
        height = 480
        BLACK = 0

        def __init__(self):
            self.set_image_calls = 0
            self.show_calls = 0

        def set_border(self, c):
            pass

        def set_image(self, img, saturation=0.5):
            self.set_image_calls += 1

        def show(self, busy_wait=True):
            self.show_calls += 1

    real_drv_mod.Inky = RealDriver

    def real_auto(ask_user=True, verbose=False):
        # Mimic upstream: import the driver at call time.
        from inky.inky_ac073tc1a import Inky as _Inky
        return _Inky()

    real_pkg.auto = real_auto
    real_pkg.inky_ac073tc1a = real_drv_mod
    sys.modules["inky"] = real_pkg
    sys.modules["inky.inky_ac073tc1a"] = real_drv_mod

    # ── Reproduce main.py's --hardware sequence ──
    # 1. Stash real inky reference and resolve the driver BEFORE mocks
    #    shadow sys.modules (this is the order main.py enforces).
    import inky as _stashed_real_inky
    _emulator_state["real_inky"] = _stashed_real_inky
    _emulator_state["real_inky_device"] = _stashed_real_inky.auto(
        ask_user=True, verbose=True
    )

    # 2. Install our mocks.
    from emulator.mocks import install_inky_mocks
    install_inky_mocks()

    # 3. Create display and init_hardware.
    display = _make_display()
    display.init_hardware()

    # ── Assertions ──
    hw = display._hw_device
    assert isinstance(hw, RealDriver), (
        "install_inky_mocks shadowed real inky's deferred driver import. "
        f"Got {type(hw).__module__}.{type(hw).__name__} — expected the "
        "RealDriver defined in this test."
    )

    # And a full render() must reach the real driver's show().
    display.render(_blank_buffer())
    assert hw.show_calls == 1, "show() was not called on the real driver"
    assert hw.set_image_calls == 1, "set_image was not called on the real driver"
