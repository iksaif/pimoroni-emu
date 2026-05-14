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


# ───────────────────────── HardwareTracer ────────────────────────────

def test_hardware_tracer_forwards_calls_and_returns_values():
    """Tracer must transparently forward calls and return whatever the
    wrapped object returned."""
    from emulator.hardware.tracer import HardwareTracer

    class FakeDriver:
        width = 800
        height = 480
        BLACK = 0

        def __init__(self):
            self.calls = []

        def set_image(self, image, saturation=0.5):
            self.calls.append(("set_image", saturation))
            return None

        def show(self, busy_wait=True):
            self.calls.append(("show", busy_wait))
            return 42  # nonsense return — we want to confirm passthrough

    inner = FakeDriver()
    tracer = HardwareTracer(inner)

    # Attribute reads pass through silently.
    assert tracer.width == 800
    assert tracer.BLACK == 0

    # Method calls forward and return the wrapped result.
    assert tracer.set_image("img", saturation=0.7) is None
    assert tracer.show(busy_wait=False) == 42
    assert inner.calls == [("set_image", 0.7), ("show", False)]


def test_hardware_tracer_logs_each_call(capsys):
    """When --trace is on, each method call produces entry+exit log lines."""
    from emulator.hardware.tracer import HardwareTracer

    class FakeDriver:
        def show(self):
            return None

    _emulator_state["trace"] = True
    tracer = HardwareTracer(FakeDriver())
    tracer.show()

    out = capsys.readouterr().out
    assert "[Hardware] -> show()" in out, f"missing entry line. got:\n{out}"
    assert "[Hardware] <- show -> None" in out, f"missing exit line. got:\n{out}"


def test_hardware_tracer_silent_without_trace(capsys):
    """When --trace is off, the tracer must not print entry/exit lines."""
    from emulator.hardware.tracer import HardwareTracer

    class FakeDriver:
        def show(self):
            return None

    _emulator_state["trace"] = False
    tracer = HardwareTracer(FakeDriver())
    tracer.show()

    out = capsys.readouterr().out
    assert "[Hardware]" not in out, f"tracer printed without --trace:\n{out}"


def test_hardware_tracer_logs_exception_with_elapsed_then_reraises(capsys):
    """When the wrapped method raises, we log it (with type, message,
    elapsed time) and let the exception propagate. Errors must surface
    *regardless* of --trace — they're not diagnostics."""
    from emulator.hardware.tracer import HardwareTracer

    class FakeDriver:
        def show(self):
            raise RuntimeError("panel offline")

    _emulator_state["trace"] = False  # explicitly off
    tracer = HardwareTracer(FakeDriver())
    with pytest.raises(RuntimeError, match="panel offline"):
        tracer.show()

    out = capsys.readouterr().out
    assert "[Hardware] !!" in out, f"errors should surface even with --trace off:\n{out}"
    assert "show" in out
    assert "RuntimeError" in out
    assert "panel offline" in out


# ──────────────────── stdlib shadow warnings ─────────────────────────

def test_warn_if_shadowing_stdlib_fires_only_with_hardware(capsys):
    """The warning helper must stay quiet when --hardware is off and
    fire on stderr when it's on, listing every concerning module name."""
    from emulator.mocks import _warn_if_shadowing_stdlib

    # No warning when --hardware is unset.
    _emulator_state["hardware"] = False
    _warn_if_shadowing_stdlib(["time", "gc"])
    err = capsys.readouterr().err
    assert err == "", f"unexpected warning when --hardware off:\n{err}"

    # Warning when --hardware is set, listing the concerning names.
    _emulator_state["hardware"] = True
    _warn_if_shadowing_stdlib(["time", "gc", "picographics"])
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "'time'" in err
    assert "'gc'" in err
    # Non-stdlib mock names shouldn't be listed.
    assert "picographics" not in err


def test_install_mocks_emits_shadow_warning_under_hardware(capsys):
    """The real install_mocks() must trigger the warning when --hardware is set."""
    from emulator.mocks import install_mocks

    _emulator_state["hardware"] = True
    install_mocks(device_name="inky_impression")

    err = capsys.readouterr().err
    assert "WARNING" in err, f"expected shadow warning, got stderr:\n{err}"
    assert "time" in err
    assert "gc" in err
