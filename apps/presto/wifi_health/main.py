"""WiFi Health Monitor — Presto (480x480, touch).

Adapted from the Tufty 2350 design (320x240) for Presto's larger touch
display. CRT-themed terminal aesthetic, 3 screens, touch tab navigation.

Run from the repo root:
    python -m emulator --device presto apps/presto/wifi_health/main.py
"""

import sys
import time

# Make module-style imports work in the emulator (which runs the file by
# path). On MicroPython the working dir is the script dir, so this is a no-op.
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from presto import Presto

import current as current_screen
import log as log_screen
import settings as settings_screen
import theme
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


def _try_connect(presto, sampler):
    """Best-effort WiFi connect. Failure is non-fatal — sim profiles work
    without a working network and real-net failures surface as DOWN states."""
    try:
        # Look for secrets, fall back to a placeholder so the emulator's WLAN
        # mock has something to record.
        try:
            from secrets import WIFI_PASSWORD, WIFI_SSID
            presto.connect(WIFI_SSID, WIFI_PASSWORD, timeout=10)
        except ImportError:
            presto.connect("emulator", "", timeout=2)
    except Exception:
        pass
    # Force one immediate sample so the first frame isn't blank
    sampler.tick(force=True)


def _update_leds(presto, sampler):
    """Reflect overall status on the 7 ring LEDs."""
    latest = sampler.latest
    gw = latest["gateway"]["status"]
    nt = latest["internet"]["status"]
    if "down" in (gw, nt):
        col = theme.DOWN
    elif "warn" in (gw, nt):
        col = theme.WARN
    else:
        col = theme.FG
    # Quarter brightness so they tint rather than glare
    r, g, b = (c // 4 for c in col)
    presto.set_all_leds_rgb(r, g, b)
    presto.set_led_brightness(0.5)


def main():
    presto = Presto(full_res=True)
    display = presto.display
    presto.set_backlight(0.8)

    display.set_font("bitmap8")

    sampler = Sampler(profile="NORMAL")
    settings_state = settings_screen.SettingsState()

    _try_connect(presto, sampler)

    screen = _os.environ.get("WIFI_HEALTH_SCREEN", "current")
    tab_regions = []
    touch_was_down = False
    last_touch_handled_at = 0

    while True:
        # ── Sample ────────────────────────────────────────────────
        if sampler.tick():
            _update_leds(presto, sampler)

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

        # Footer + version stamp
        tab_regions = theme.draw_footer(display, active=screen)
        vw = display.measure_text(VERSION, scale=theme.SCALE_TINY)
        display.set_pen(theme.pen(display, theme.DIM))
        display.text(VERSION, theme.WIDTH - 4 - vw, theme.HEIGHT - 12,
                     scale=theme.SCALE_TINY)

        presto.update()

        # ── Input (edge-triggered) ────────────────────────────────
        presto.touch_poll()
        t = presto.touch
        if t.state and not touch_was_down:
            now = time.time()
            if now - last_touch_handled_at > 0.12:  # debounce
                last_touch_handled_at = now
                x, y = int(t.x), int(t.y)
                # Tab hit?
                for key, rx, ry, rw, rh in tab_regions:
                    if rx <= x < rx + rw and ry <= y < ry + rh:
                        screen = key
                        break
                else:
                    # Per-screen hits
                    if screen == "settings":
                        hit = settings_screen.hit_test(settings_state, x, y)
                        if hit:
                            # Right half decreases, left half/middle increases
                            settings_state.cycle(hit, direction=1)
                            if hit == "profile":
                                sampler.profile = settings_state.values["profile"]
                            elif hit == "interval":
                                sampler.sample_period = int(
                                    settings_state.values["interval"].rstrip("s")
                                )
                            elif hit == "target":
                                sampler.net_target = settings_state.values["target"]
                            elif hit == "bright":
                                presto.set_backlight(
                                    int(settings_state.values["bright"]) / 5.0
                                )
        touch_was_down = bool(t.state)

        # Cap framerate; lets the cursor blink visibly without busy looping
        time.sleep(0.08)


if __name__ == "__main__":
    main()
