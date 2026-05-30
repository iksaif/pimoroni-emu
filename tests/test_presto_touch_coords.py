"""Tests for Presto touch coordinates scaling."""

import sys
import pytest
from emulator import _emulator_state
from emulator.devices.presto import PrestoDevice
from emulator.hardware.touch import TouchManager
from emulator.mocks.presto import Presto


@pytest.fixture(autouse=True)
def _isolate_emulator_state():
    saved_state = dict(_emulator_state)
    _emulator_state.clear()
    yield
    _emulator_state.clear()
    _emulator_state.update(saved_state)


def test_presto_touch_scaling_half_res():
    # Setup device config
    device = PrestoDevice()
    _emulator_state["device"] = device

    # TouchManager handles mapping from pygame window space
    touch_manager = TouchManager(device)

    # Presto mock (full_res=False, which is default)
    presto = Presto(full_res=False)

    # Find window center coordinates
    disp_rect = device.get_display_rect()
    win_x = disp_rect[0] + 240
    win_y = disp_rect[1] + 240

    # Click at center of window (corresponding to display coordinates 240, 240)
    touch_manager.handle_mouse_down(win_x, win_y)

    # Poll touch state
    presto.touch_poll()

    # In half res mode, coordinate space is 240x240, so display coords 240, 240 map to 120, 120
    touch_a = presto.touch_a
    assert touch_a.x == 120
    assert touch_a.y == 120
    assert touch_a.touched is True


def test_presto_touch_scaling_full_res():
    # Setup device config
    device = PrestoDevice()
    _emulator_state["device"] = device

    # TouchManager handles mapping from pygame window space
    touch_manager = TouchManager(device)

    # Presto mock (full_res=True)
    presto = Presto(full_res=True)

    # Find window center coordinates
    disp_rect = device.get_display_rect()
    win_x = disp_rect[0] + 240
    win_y = disp_rect[1] + 240

    # Click at center of window (corresponding to display coordinates 240, 240)
    touch_manager.handle_mouse_down(win_x, win_y)

    # Poll touch state
    presto.touch_poll()

    # In full res mode, coordinate space is 480x480, so display coords 240, 240 map to 240, 240
    touch_a = presto.touch_a
    assert touch_a.x == 240
    assert touch_a.y == 240
    assert touch_a.touched is True
