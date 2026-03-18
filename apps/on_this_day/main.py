"""On This Day — daily historical events for kids.

Entry point. Run: python -m emulator --device presto apps/on_this_day/main.py
"""

import time

from config import (
    WIFI_SSID, AI_API_KEY, AUTO_CYCLE_SECS, SKIP_BOOT,
    NORMAL_BRIGHTNESS, DIM_BRIGHTNESS, SLEEP_BRIGHTNESS, SLEEP_AFTER_SECS,
    s, capitalize, utc_to_local, is_night,
)

# ─── Device init ─────────────────────────────────────────────────
presto = None
try:
    from presto import Presto
    presto = Presto(full_res=True)
    display = presto.display
except ImportError:
    from picographics import PicoGraphics
    display = PicoGraphics()

WIDTH, HEIGHT = display.get_bounds()

# ─── Crash handler ───────────────────────────────────────────────
from crash import show_crash

# ─── SD card ─────────────────────────────────────────────────────
STORAGE_DIR = "."
try:
    import machine as _m
    import sdcard as _sdcard
    _sd_spi = _m.SPI(0, sck=_m.Pin(34, _m.Pin.OUT), mosi=_m.Pin(35, _m.Pin.OUT), miso=_m.Pin(36, _m.Pin.OUT))
    _sd = _sdcard.SDCard(_sd_spi, _m.Pin(39))
    try:
        import uos
        uos.mount(_sd, "/sd")
    except Exception:
        import os
        os.mount(_sd, "/sd")
    # Quick write test
    with open("/sd/.test", "w") as f:
        f.write("ok")
    import os
    os.remove("/sd/.test")
    STORAGE_DIR = "/sd"
    print("[sd] mounted /sd")
except Exception:
    pass

CACHE_FILE = STORAGE_DIR + "/day_cache.json"
ICON_DIR = STORAGE_DIR + "/icon_cache"

# ─── Drawing init ────────────────────────────────────────────────
import draw
now = time.localtime()
draw.init(display, presto, WIDTH, HEIGHT, now[0], now[1], now[2])
today_year, today_month, today_day = now[0], now[1], now[2]

# ─── Boot + main loop ───────────────────────────────────────────
try:
    from fetch import connect_wifi, is_wifi_connected, fetch_events, ai_rewrite, load_cache, save_cache

    draw.boot_screen("...", 0)

    # Step 1: WiFi
    wifi_ok = False
    if SKIP_BOOT:
        draw.boot_screen("Skip boot", 2, draw.DIM)
    elif WIFI_SSID:
        draw.boot_screen(s("wifi_connect") + "...", 0)
        wifi_ok = connect_wifi()
        draw.boot_screen(s("wifi_ok") if wifi_ok else s("wifi_fail"), 1,
                         draw.OK_PEN if wifi_ok else draw.ERR_PEN)
    else:
        draw.boot_screen(s("no_wifi_cfg"), 1, draw.DIM)
    time.sleep(0.3)

    # Step 2: NTP
    if wifi_ok:
        draw.boot_screen(s("time_sync") + "...", 1)
        import machine
        import ntptime
        rtc = machine.RTC()
        synced = False
        for _ in range(3):
            try:
                ntptime.settime()
                utc = time.localtime()
                if utc[0] >= 2025:
                    local = utc_to_local(utc)
                    rtc.datetime((local[0], local[1], local[2], local[6],
                                  local[3], local[4], local[5], 0))
                    synced = True
                    break
            except Exception:
                pass
            time.sleep(1)
        draw.boot_screen(s("time_ok") if synced else s("time_fail"), 2,
                         draw.OK_PEN if synced else draw.ERR_PEN)
    time.sleep(0.3)

    # Step 3-4: Cache or fetch + AI
    events = load_cache(CACHE_FILE)
    if events:
        draw.boot_screen("Cache OK !", 4, draw.OK_PEN)
        time.sleep(0.3)
    else:
        events = fetch_events(today_month, today_day) if wifi_ok else []
        if events:
            draw.boot_screen("{} events !".format(len(events)), 3, draw.OK_PEN)
        else:
            draw.boot_screen(s("no_events") if wifi_ok else s("fetch_fail"), 3, draw.ERR_PEN)
        time.sleep(0.3)

        if AI_API_KEY and events:
            for attempt in range(3):
                draw.boot_screen(s("ai_rewrite") + "... {}/3".format(attempt + 1), 3)
                rewritten, err = ai_rewrite(events)
                if rewritten:
                    events = rewritten
                    draw.boot_screen(s("ai_rewrite") + " OK !", 4, draw.OK_PEN)
                    break
                draw.boot_screen((err or "?")[:25], 3, draw.ERR_PEN)
                time.sleep(1.5)
            else:
                events = [(e[0], capitalize(e[1]), e[2], e[3] if len(e) > 3 else "",
                           e[4] if len(e) > 4 else False) for e in events]
        time.sleep(0.3)
        if events:
            save_cache(CACHE_FILE, events)

    # Step 5: Icons
    icon_loader = None
    try:
        from icons import IconLoader
        icon_loader = IconLoader(display, size=28, cache_dir=ICON_DIR)
        tags = set()
        for ev in events:
            if len(ev) > 2:
                tags.update(ev[2])
        if tags and is_wifi_connected():
            draw.boot_screen("Icons...", 4)
            icon_loader.ensure_many(tags)
    except Exception:
        icon_loader = None

    draw.boot_screen(s("ready"), 5, draw.OK_PEN)
    time.sleep(0.4)

    # ─── Main loop ───────────────────────────────────────────
    if presto:
        presto.set_backlight(NORMAL_BRIGHTNESS)

    current = 0
    last_touch = False
    sleeping = False
    needs_redraw = True
    ticks = time.ticks_ms if hasattr(time, "ticks_ms") else lambda: int(time.time() * 1000)
    t0 = ticks()
    last_cycle = last_input = last_wifi_retry = t0
    transition_end = 0
    prev_event = -1

    while True:
        now_ms = ticks()
        t = (now_ms - t0) / 1000.0

        # Day change
        if int(t) % 3 == 0:
            if time.localtime()[2] != today_day:
                try:
                    import machine
                    machine.reset()
                except Exception:
                    pass

        # WiFi retry
        if WIFI_SSID and not is_wifi_connected() and not SKIP_BOOT:
            if (now_ms - last_wifi_retry) > 60000:
                last_wifi_retry = now_ms
                connect_wifi()

        # Night dimming
        if presto and not sleeping:
            presto.set_backlight(DIM_BRIGHTNESS if is_night() else NORMAL_BRIGHTNESS)

        # Input
        user_input = False
        if draw.HAS_TOUCH:
            touch = presto.touch_a
            pressed = touch.touched and not last_touch
            last_touch = touch.touched
            user_input = pressed
        else:
            try:
                from machine import Pin
                for p in (12, 13, 14, 15):
                    if Pin(p, Pin.IN, Pin.PULL_UP).value() == 0:
                        user_input = True
                        break
            except Exception:
                pass

        if user_input:
            last_input = now_ms
            if sleeping:
                sleeping = False
                if presto:
                    presto.set_backlight(DIM_BRIGHTNESS if is_night() else NORMAL_BRIGHTNESS)
            elif events:
                prev_event = current
                current = (current + 1) % len(events)
                last_cycle = now_ms
                needs_redraw = True
                if not draw.IS_EINK:
                    transition_end = now_ms + 400
            if not draw.HAS_TOUCH:
                time.sleep(0.2)

        # Sleep
        if presto and not sleeping and SLEEP_AFTER_SECS > 0:
            if (now_ms - last_input) > SLEEP_AFTER_SECS * 1000:
                sleeping = True
                presto.set_backlight(SLEEP_BRIGHTNESS)

        # Auto-cycle
        if events and AUTO_CYCLE_SECS > 0 and not sleeping:
            if (now_ms - last_cycle) / 1000.0 >= AUTO_CYCLE_SECS:
                prev_event = current
                current = (current + 1) % len(events)
                last_cycle = now_ms
                needs_redraw = True
                if not draw.IS_EINK:
                    transition_end = now_ms + 400

        # Draw
        if draw.IS_EINK:
            if needs_redraw:
                draw.draw_frame(events, current, t, icon_loader)
                needs_redraw = False
            time.sleep(0.1)
        elif transition_end > now_ms:
            progress = 1.0 - ((transition_end - now_ms) / 400.0)
            if progress < 0.5:
                draw.draw_frame(events, prev_event if prev_event >= 0 else current, t, icon_loader, 1.0 - progress * 2)
            else:
                draw.draw_frame(events, current, t, icon_loader, (progress - 0.5) * 2)
        else:
            draw.draw_frame(events, current, t, icon_loader)
            time.sleep(0.05)

except Exception as e:
    show_crash(display, presto, e)
