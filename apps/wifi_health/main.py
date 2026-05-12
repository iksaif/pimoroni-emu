"""WiFi Health Monitor — Presto and Tufty 2350.

CRT-themed terminal aesthetic, 3 screens (Current / Log / Settings).
Adapts automatically to the host device:
  * Presto    480x480 touchscreen, ring LEDs reflect status, touch tabs
  * Tufty     320x240 LCD, A/B/C buttons switch screens, UP/DOWN navigate
              the settings list and A cycles the selected option

Run from the repo root:
    python -m emulator --device presto apps/wifi_health/main.py
    python -m emulator --device tufty  apps/wifi_health/main.py
"""

import os as _os
import sys
import time

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import current as current_screen
import log as log_screen
import settings as settings_screen
import theme
from device import detect
from sampler import Sampler

VERSION = "v0.4"


def _hms():
    t = time.localtime()
    return "{:02d}:{:02d}".format(t[3], t[4])


def _mode_label(screen):
    return {
        "current":  "CURRENT",
        "log":      "LOG . 24h",
        "settings": "SETTINGS",
    }.get(screen, "")


def _try_connect(device, sampler):
    """Best-effort WiFi connect. Failure is non-fatal."""
    try:
        try:
            from secrets import WIFI_PASSWORD, WIFI_SSID
            ssid, password = WIFI_SSID, WIFI_PASSWORD
        except ImportError:
            ssid, password = "emulator", ""
        if device.kind == "presto":
            device._presto.connect(ssid, password, timeout=10)
        else:
            # Tufty: bare network module
            import network
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            wlan.connect(ssid, password)
    except Exception:
        pass
    sampler.tick(force=True)


def _status_colour(latest):
    gw = latest["gateway"]["status"]
    nt = latest["internet"]["status"]
    if "down" in (gw, nt):
        return theme.DOWN
    if "warn" in (gw, nt):
        return theme.WARN
    return theme.FG


def _apply_setting(device, sampler, settings_state, key):
    """Push a settings change into the live state."""
    if key == "profile":
        sampler.profile = settings_state.values["profile"]
    elif key == "interval":
        sampler.sample_period = int(settings_state.values["interval"].rstrip("s"))
    elif key == "target":
        sampler.net_target = settings_state.values["target"]
    elif key == "bright":
        device.set_backlight(int(settings_state.values["bright"]) / 5.0)


def main():
    device = detect()
    display = device._display
    theme.init(device)
    display.set_font("bitmap8")
    device.set_backlight(0.8)

    sampler = Sampler(profile="NORMAL")
    settings_state = settings_screen.SettingsState()

    _try_connect(device, sampler)

    screen = _os.environ.get("WIFI_HEALTH_SCREEN", "current")
    tab_regions = []

    # Edge detection state
    touch_was_down = False
    last_touch_handled_at = 0.0
    button_prev = {}

    while True:
        # ── Sample ────────────────────────────────────────────────
        if sampler.tick():
            device.status_leds(_status_colour(sampler.latest))

        # ── Frame ─────────────────────────────────────────────────
        display.set_pen(theme.pen(display, theme.BG))
        display.clear()
        theme.draw_header(display, _mode_label(screen), _hms())

        if screen == "current":
            current_screen.draw(display, sampler)
        elif screen == "log":
            log_screen.draw(display, sampler)
        else:
            settings_screen.draw(display, settings_state)

        tab_regions = theme.draw_footer(display, active=screen)
        vw = display.measure_text(VERSION, scale=theme.SCALE_TINY)
        display.set_pen(theme.pen(display, theme.DIM))
        display.text(VERSION, theme.WIDTH - 4 - vw, theme.HEIGHT - 12,
                     scale=theme.SCALE_TINY)

        device.update()

        # ── Input ─────────────────────────────────────────────────
        if device.has_touch:
            x, y, pressed = device.read_touch()
            if pressed and not touch_was_down:
                now = time.time()
                if now - last_touch_handled_at > 0.12:
                    last_touch_handled_at = now
                    handled = False
                    for key, rx, ry, rw, rh in tab_regions:
                        if rx <= x < rx + rw and ry <= y < ry + rh:
                            screen = key
                            handled = True
                            break
                    if not handled and screen == "settings":
                        hit = settings_screen.hit_test(settings_state, x, y)
                        if hit:
                            settings_state.cycle(hit, direction=1)
                            _apply_setting(device, sampler, settings_state, hit)
            touch_was_down = bool(pressed)

        else:
            # Tufty buttons (edge-triggered)
            held = device.read_buttons()
            for name, is_down in held.items():
                fired = is_down and not button_prev.get(name, False)
                button_prev[name] = is_down
                if not fired:
                    continue
                if name == "A":
                    if screen == "settings":
                        # On settings, A cycles the selected option
                        key = settings_state.selected_key()
                        settings_state.cycle(key, direction=1)
                        _apply_setting(device, sampler, settings_state, key)
                    else:
                        screen = "current"
                elif name == "B":
                    screen = "log"
                elif name == "C":
                    screen = "settings"
                elif name == "UP":
                    if screen == "settings":
                        settings_state.move(-1)
                elif name == "DOWN":
                    if screen == "settings":
                        settings_state.move(1)

        time.sleep(0.08)


if __name__ == "__main__":
    main()
