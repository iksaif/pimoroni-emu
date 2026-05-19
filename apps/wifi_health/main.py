"""WiFi Health Monitor — Presto edition.

CRT-themed terminal aesthetic, 3 screens (Current / Log / Settings).
Targets the Presto's 480x480 touchscreen — ring LEDs reflect status,
touch tabs switch screens.

For Tufty 2350 see apps/wifi_health_tufty/ (separate codebase because
the Tufty's badgeware API differs significantly from PicoGraphics).

Run from the repo root:
    python -m emulator --device presto apps/wifi_health/main.py
"""

import os as _os
import sys
import time

# CPython emulator: insert the script's directory on sys.path so sibling
# imports work. MicroPython doesn't ship os.path and modules sit at the
# filesystem root, so this whole block is a no-op there.
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))  # type: ignore[attr-defined]
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
except (AttributeError, NameError):
    pass

import current as current_screen
import leds
import log as log_screen
import settings as settings_screen
import theme
from device import detect
from sampler import Sampler

VERSION = "v0.4"


# ─── Logging ─────────────────────────────────────────────────────────
LOG_PATH = "/wifi_health.log"
_LOG_F = None


def _log(msg):
    """Append a line to both stdout and the on-device log file.

    Lets us debug after a reboot without needing a live serial session.
    """
    line = "[wh] " + msg
    print(line)
    global _LOG_F
    try:
        if _LOG_F is None:
            _LOG_F = open(LOG_PATH, "a")
        _LOG_F.write(line + "\n")
        _LOG_F.flush()
    except Exception:
        _LOG_F = None


def _log_rotate():
    try:
        with open(LOG_PATH, "w") as f:
            f.write("--- boot ---\n")
    except Exception:
        pass


def _hms():
    t = time.localtime()
    return "{:02d}:{:02d}".format(t[3], t[4])


def _mode_label(screen):
    return {
        "current":  "CURRENT",
        "log":      "LOG . 24h",
        "settings": "SETTINGS",
    }.get(screen, "")


def _draw_boot(device, line, sub=None, spinner_phase=0):
    """Draw a centred CRT-style boot screen with an animated spinner.

    Called repeatedly during the connect phase so the user has visual
    feedback while WiFi negotiates.
    """
    display = device._display
    display.set_pen(theme.pen(display, theme.BG))
    display.clear()

    title = "> WIFI HEALTH"
    tw = display.measure_text(title, scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.FG))
    display.text(title, (theme.WIDTH - tw) // 2,
                 theme.HEIGHT // 2 - 60, scale=theme.SCALE_BODY)

    # Main status line
    lw = display.measure_text(line, scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.FG))
    display.text(line, (theme.WIDTH - lw) // 2,
                 theme.HEIGHT // 2 - 8, scale=theme.SCALE_BODY)

    # Spinner: a row of dots, one of them brightened
    dots = ".  .  .  .  .  ."
    dw = display.measure_text(dots, scale=theme.SCALE_BODY)
    base_x = (theme.WIDTH - dw) // 2
    display.set_pen(theme.pen(display, theme.DIM))
    display.text(dots, base_x, theme.HEIGHT // 2 + 24, scale=theme.SCALE_BODY)
    # Highlight one dot based on phase
    dot_w = dw // 6
    hx = base_x + (spinner_phase % 6) * dot_w + dot_w // 2 - 2
    display.set_pen(theme.pen(display, theme.FG))
    display.rectangle(hx, theme.HEIGHT // 2 + 28, 6, 6)

    if sub:
        sw = display.measure_text(sub, scale=theme.SCALE_TINY)
        display.set_pen(theme.pen(display, theme.DIM))
        display.text(sub, (theme.WIDTH - sw) // 2,
                     theme.HEIGHT // 2 + 60, scale=theme.SCALE_TINY)

    device.update()


def _boot_leds(device, phase):
    """Cyan/green sweep around the ring during boot."""
    colors = []
    for i in range(device.NUM_LEDS):
        on = (i == phase % device.NUM_LEDS)
        colors.append(theme.FG if on else theme.SCAN)
    device.set_leds(colors)


def _try_connect(device, sampler):
    """Best-effort WiFi connect with on-screen feedback. Failure is non-fatal."""
    try:
        from secrets import WIFI_PASSWORD, WIFI_SSID
        ssid, password = WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        ssid, password = "emulator", ""

    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            wlan.connect(ssid, password)
    except Exception:
        wlan = None

    # Always animate for ≥ MIN_FRAMES so the loader is visible even when
    # the radio has cached credentials and associates in <300 ms.
    MIN_FRAMES = 10           # 10 * 0.15s ≈ 1.5s minimum dwell
    MAX_FRAMES = 80           # ≈ 12s ceiling — give up after that
    phase = 0
    while phase < MAX_FRAMES:
        connected = wlan is not None and wlan.isconnected()
        if phase >= MIN_FRAMES and connected:
            break
        line = "CONNECTING . " + ssid if not connected else "WIFI OK"
        sub = "WiFi handshake" if not connected else wlan.ifconfig()[0]
        _draw_boot(device, line, sub=sub, spinner_phase=phase)
        _boot_leds(device, phase)
        phase += 1
        time.sleep(0.15)

    if wlan is not None and wlan.isconnected():
        ip = wlan.ifconfig()[0]
        _draw_boot(device, "ONLINE", sub=ip, spinner_phase=phase)
        time.sleep(0.6)
    else:
        _draw_boot(device, "OFFLINE", sub="probes will report DOWN",
                   spinner_phase=phase)
        time.sleep(0.8)

    sampler.tick(force=True)


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
    _log_rotate()
    _log("main() entered")
    try:
        device = detect()
    except Exception as e:
        _log("detect() failed: " + repr(e))
        raise
    _log("device kind={} size={}x{} touch={}".format(
        device.kind, device.width, device.height, device.has_touch))
    display = device._display
    theme.init(device)
    display.set_font("bitmap8")
    device.set_backlight(0.8)
    _log("display+theme initialised, backlight set")

    sampler = Sampler(profile="NORMAL")
    settings_state = settings_screen.SettingsState()
    _log("sampler+settings ready")

    _try_connect(device, sampler)
    _log("_try_connect returned")

    try:
        screen = _os.environ.get("WIFI_HEALTH_SCREEN", "current")
    except AttributeError:
        screen = "current"  # MicroPython: no environ
    tab_regions = []

    # Edge detection state
    touch_was_down = False
    last_touch_handled_at = 0.0
    button_prev = {}

    last_led_update = 0.0
    frame_count = 0
    _log("entering main loop, initial screen={}".format(screen))
    while True:
        # ── Sample ────────────────────────────────────────────────
        sampler.tick()

        # ── LEDs (refresh ~3x/s so breathing/flashing animates) ──
        now = time.time()
        if now - last_led_update > 0.3:
            device.set_leds(leds.pattern_for(screen, sampler))
            last_led_update = now

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
        frame_count += 1
        if frame_count <= 3 or frame_count % 60 == 0:
            _log("frame {} screen={}".format(frame_count, screen))

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
    try:
        main()
    except Exception as _e:
        import sys
        _log("FATAL: " + repr(_e))
        try:
            sys.print_exception(_e)
        except Exception:
            pass
        raise
