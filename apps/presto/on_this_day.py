"""On This Day — today's date and a historical event from Wikipedia.

Fetches curated events and notable births from Wikipedia's "On This Day" API
and cycles through them. Touch the screen (Presto) or wait to see the next event.

Optionally uses a free AI API (Groq, Gemini, or Mistral) to reformulate
events for children and pick emojis (rendered via Twemoji PNGs).

Features: daily cache, SD card support, night dimming, sleep on inactivity,
WiFi retry, crash screen, .env config.

Works on Presto (primary) and other PicoGraphics devices.
Run: python -m emulator --device presto apps/presto/on_this_day.py
"""

import math
import time

# Load .env file if present (works on both desktop and MicroPython)
_env = {}
try:
    with open(".env") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _env[_k.strip()] = _v.strip()
except OSError:
    pass
try:
    import os
    for _k in ("WIFI_SSID", "WIFI_PASSWORD", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL"):
        _v = os.environ.get(_k)
        if _v is not None:
            _env.setdefault(_k, _v)
except (ImportError, AttributeError):
    pass

# ─── Configuration ───────────────────────────────────────────────
LANGUAGE = "fr"
WIFI_SSID = _env.get("WIFI_SSID", "")
WIFI_PASSWORD = _env.get("WIFI_PASSWORD", "")
UTC_OFFSET_WINTER = 1
UTC_OFFSET_SUMMER = 2
AUTO_CYCLE_SECS = 30
DARK_THEME = True

# AI reformulation
AI_PROVIDER = _env.get("AI_PROVIDER", "groq")
AI_API_KEY = _env.get("AI_API_KEY", "")
AI_MODEL = _env.get("AI_MODEL", "")
KID_AGE = 10

# Night dimming (24h format, local time)
DIM_HOUR_START = 20   # dim after 20:00
DIM_HOUR_END = 7      # bright after 07:00
DIM_BRIGHTNESS = 0.15
NORMAL_BRIGHTNESS = 1.0

# Sleep on inactivity
SLEEP_AFTER_SECS = 300  # dim to sleep after 5min of no touch
SLEEP_BRIGHTNESS = 0.02

SKIP_BOOT = _env.get("SKIP_BOOT", "") != ""
# ─────────────────────────────────────────────────────────────────

_AI_DEFAULTS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.0-flash",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-small-latest",
    },
}

_MONTHS = {
    "fr": ["janvier", "fevrier", "mars", "avril", "mai", "juin",
           "juillet", "aout", "septembre", "octobre", "novembre", "decembre"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "de": ["Januar", "Februar", "Marz", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "pt": ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
}

_AGO_FMT = {
    "fr": "il y a {} ans", "en": "{} years ago", "de": "vor {} Jahren",
    "es": "hace {} anos", "it": "{} anni fa", "pt": "ha {} anos",
}

_STRINGS = {
    "fr": {
        "title": "Ce jour dans l'histoire",
        "wifi_connect": "WiFi", "wifi_ok": "WiFi OK !",
        "wifi_fail": "WiFi echoue", "no_wifi_cfg": "WiFi non configure",
        "time_sync": "Heure", "time_ok": "Heure OK !",
        "time_fail": "Pas d'heure",
        "fetch": "Chargement", "fetch_fail": "Erreur chargement",
        "no_events": "Aucun evenement", "network_err": "Erreur reseau",
        "ready": "C'est parti !", "ai_rewrite": "Simplification",
        "born": "Naissance de",
    },
    "en": {
        "title": "On This Day",
        "wifi_connect": "WiFi", "wifi_ok": "WiFi OK!",
        "wifi_fail": "WiFi failed", "no_wifi_cfg": "WiFi not set",
        "time_sync": "Time sync", "time_ok": "Time OK!",
        "time_fail": "No time source",
        "fetch": "Fetching", "fetch_fail": "Fetch failed",
        "no_events": "No events found", "network_err": "Network error",
        "ready": "Ready!", "ai_rewrite": "Simplifying",
        "born": "Born:",
    },
}

_LANG_NAMES = {
    "fr": "French", "en": "English", "de": "German",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese",
}


def _s(key):
    strings = _STRINGS.get(LANGUAGE, _STRINGS.get("en", {}))
    return strings.get(key, _STRINGS.get("en", {}).get(key, key))


def _month_name(m):
    return _MONTHS.get(LANGUAGE, _MONTHS.get("en"))[m - 1]


def _years_ago_str(y):
    return _AGO_FMT.get(LANGUAGE, _AGO_FMT["en"]).format(y)


def _capitalize(text):
    """Capitalize first letter (Wikipedia FR events start lowercase)."""
    if text and text[0].islower():
        return text[0].upper() + text[1:]
    return text


# ─── Device init ─────────────────────────────────────────────────
presto = None
try:
    from presto import Presto
    presto = Presto(full_res=True)
    display = presto.display
except ImportError:
    # Not a Presto — use PicoGraphics with auto-detection.
    # On real hardware, pass the correct DISPLAY_* constant for your board.
    # The emulator auto-detects from --device flag.
    from picographics import PicoGraphics
    display = PicoGraphics()

WIDTH, HEIGHT = display.get_bounds()

# ─── Device capabilities ─────────────────────────────────────────
HAS_TOUCH = presto is not None
IS_EINK = WIDTH > 400 and HEIGHT > 200 and presto is None
IS_SMALL = WIDTH < 320 or HEIGHT < 200   # Badger (296x128)
IS_MEDIUM = not IS_SMALL and (WIDTH < 480 or HEIGHT < 300)  # Tufty (320x240)

# Adaptive scales based on resolution
if IS_SMALL:
    _S_TITLE = 2
    _S_YEAR = 2
    _S_NAME = 1
    _S_BODY_BIG = 2
    _S_BODY_SM = 1
    _S_AGO = 1
    _S_BOOT_TITLE = 2
    _S_BOOT_MSG = 1
elif IS_MEDIUM:
    _S_TITLE = 2
    _S_YEAR = 2
    _S_NAME = 1
    _S_BODY_BIG = 2
    _S_BODY_SM = 1
    _S_AGO = 1
    _S_BOOT_TITLE = 2
    _S_BOOT_MSG = 2
else:  # Large: Presto (480x480), Inky Frame (800x480)
    _S_TITLE = 4
    _S_YEAR = 4
    _S_NAME = 2
    _S_BODY_BIG = 3
    _S_BODY_SM = 2
    _S_AGO = 2
    _S_BOOT_TITLE = 4
    _S_BOOT_MSG = 3


def _show_crash(err_type, err_msg):
    try:
        import sys
        sys.print_exception(err_type) if isinstance(err_type, BaseException) else None
    except Exception:
        pass
    try:
        red = display.create_pen(255, 50, 50)
        white = display.create_pen(255, 255, 255)
        black = display.create_pen(0, 0, 0)
        display.set_pen(black)
        display.clear()
        display.set_pen(red)
        display.text("CRASH", 20, 20, -1, scale=4, spacing=1)
        display.set_pen(white)
        msg = str(err_msg)
        y = 70
        chunk = 40
        for i in range(0, len(msg), chunk):
            if y > HEIGHT - 30:
                break
            display.text(msg[i:i + chunk], 20, y, -1, scale=2, spacing=1)
            y += 22
        if presto:
            presto.update()
        else:
            display.update()
    except Exception:
        pass
    while True:
        time.sleep(1)


# ─── HSV pen helper ──────────────────────────────────────────────
_pen_cache = {}
_PEN_CACHE_MAX = 256


def hsv_pen(h, s, v):
    key = (int(h * 200), int(s * 20), int(v * 20))
    pen = _pen_cache.get(key)
    if pen is None:
        if len(_pen_cache) >= _PEN_CACHE_MAX:
            _pen_cache.clear()
        pen = display.create_pen_hsv(h % 1.0, s, v)
        _pen_cache[key] = pen
    return pen


# ─── Theme ───────────────────────────────────────────────────────
if DARK_THEME:
    BG = display.create_pen(15, 12, 30)
    TEXT = display.create_pen(230, 230, 230)
    DIM = display.create_pen(60, 50, 80)
    HEADER_BG = display.create_pen(25, 20, 50)
    ERR_PEN = display.create_pen(255, 80, 80)
    OK_PEN = display.create_pen(80, 255, 80)
    TIMESCALE_BG = display.create_pen(30, 25, 55)
else:
    BG = display.create_pen(255, 255, 255)
    TEXT = display.create_pen(0, 0, 0)
    DIM = display.create_pen(160, 160, 160)
    HEADER_BG = display.create_pen(235, 235, 240)
    ERR_PEN = display.create_pen(200, 0, 0)
    OK_PEN = display.create_pen(0, 140, 0)
    TIMESCALE_BG = display.create_pen(220, 220, 230)

WHITE = display.create_pen(255, 255, 255)


def _update():
    if presto:
        presto.update()
    else:
        display.update()


def _set_layer():
    if presto:
        display.set_layer(0)


# ─── Boot screen ─────────────────────────────────────────────────
_BOOT_STEPS = 5


def boot_screen(message, step, color=None):
    cx = WIDTH // 2
    _set_layer()
    display.set_pen(BG)
    display.clear()

    title = _s("title")
    tw = display.measure_text(title, scale=_S_BOOT_TITLE, spacing=1)
    display.set_pen(TEXT)
    display.text(title, cx - tw // 2, HEIGHT // 4 - 10 * _S_BOOT_TITLE // 2, -1, scale=_S_BOOT_TITLE, spacing=1)

    if not IS_SMALL:
        dot_y = HEIGHT // 4 + 10 * _S_BOOT_TITLE // 2 + 5
        for i in range(5):
            display.set_pen(hsv_pen(i / 5.0, 0.8, 0.85))
            display.circle(cx + (i - 2) * 20, dot_y, 3)

    bar_w = int(WIDTH * 0.7)
    bar_h = 6 if IS_SMALL else 10
    bx = cx - bar_w // 2
    by = HEIGHT // 2 - 5
    display.set_pen(DIM)
    display.rectangle(bx, by, bar_w, bar_h)

    fill = int(bar_w * step / _BOOT_STEPS)
    if fill > 0:
        for x in range(0, fill, 4):
            w = min(4, fill - x)
            display.set_pen(hsv_pen(x / bar_w, 0.8, 0.9))
            display.rectangle(bx + x, by + 1, w, bar_h - 2)

    if not IS_SMALL:
        for i in range(_BOOT_STEPS):
            dot_x = bx + int(bar_w * (i + 1) / _BOOT_STEPS)
            display.set_pen(hsv_pen(i / _BOOT_STEPS, 0.7, 0.9) if i < step else DIM)
            display.circle(dot_x, by + bar_h // 2, 4)

    display.set_pen(color if color else TEXT)
    sw = display.measure_text(message, scale=_S_BOOT_MSG, spacing=1)
    display.text(message, cx - sw // 2, HEIGHT // 2 + 15, -1, scale=_S_BOOT_MSG, spacing=1)
    _update()


# ─── Time helpers ────────────────────────────────────────────────
def _get_utc_offset():
    month = time.localtime()[1]
    return UTC_OFFSET_SUMMER if 4 <= month <= 9 else UTC_OFFSET_WINTER


def _utc_to_local(utc):
    return time.localtime(time.mktime(utc) + _get_utc_offset() * 3600)


def _time_is_sane():
    return time.localtime()[0] >= 2025


def _is_night():
    """Check if current time is in the dim period."""
    hour = time.localtime()[3]
    if DIM_HOUR_START > DIM_HOUR_END:
        return hour >= DIM_HOUR_START or hour < DIM_HOUR_END
    return DIM_HOUR_START <= hour < DIM_HOUR_END


# ─── WiFi helper ─────────────────────────────────────────────────
_wlan = None


def _connect_wifi():
    """Try to connect to WiFi. Returns True if connected."""
    global _wlan
    if not WIFI_SSID:
        return False
    try:
        import network
        if _wlan is None:
            _wlan = network.WLAN(network.STA_IF)
            _wlan.active(True)
        if _wlan.isconnected():
            return True
        _wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(100):
            if _wlan.isconnected():
                return True
            time.sleep(0.1)
    except Exception:
        pass
    return False


def _is_wifi_connected():
    return _wlan is not None and _wlan.isconnected()


# ─── AI reformulation ───────────────────────────────────────────
def _ai_rewrite(events_list):
    if not AI_API_KEY or not events_list:
        return None, "no API key"

    provider = _AI_DEFAULTS.get(AI_PROVIDER)
    if not provider:
        return None, "unknown provider"

    url = provider["url"]
    model = AI_MODEL or provider["model"]
    lang_name = _LANG_NAMES.get(LANGUAGE, "English")

    # Build index->title lookup (not year, since years can collide)
    _title_by_idx = {}
    for i, ev in enumerate(events_list):
        if len(ev) > 3 and ev[3]:
            _title_by_idx[i + 1] = ev[3]  # 1-indexed

    event_lines = []
    for i, ev in enumerate(events_list):
        is_birth = ev[4] if len(ev) > 4 else False
        tag = "[BIRTH {}]".format(ev[0] or "?") if is_birth else "[{}]".format(ev[0] or "?")
        event_lines.append("{}. {} {}".format(i + 1, tag, ev[1]))
    events_block = "\n".join(event_lines)

    prompt = (
        "You are preparing a daily \"On This Day\" display for a {age}-year-old child. "
        "The display uses a small screen with a bitmap font (ASCII only, no Unicode/emojis in text). "
        "But we CAN display a small emoji icon next to each event.\n\n"
        "Below are historical events and notable births that happened on this date.\n\n"
        "Your job:\n"
        "1. REWRITE each event so a {age}-year-old can understand, but:\n"
        "   - KEEP real names of people, places, and things\n"
        "   - KEEP specific facts (numbers, names, places)\n"
        "   - Just use simpler sentence structure\n"
        "   - 1-2 short sentences per event\n"
        "   - Text must be ASCII only (no emojis, no special chars)\n"
        "   - CAPITALIZE the first letter of each text\n"
        "   - For BIRTH entries: say WHO the person is and WHY they are famous, "
        "not just that they were born. Example: \"Rudolf Diesel, l'inventeur du "
        "moteur diesel, est ne a Paris.\"\n"
        "2. For violent/war events: {violence_rule}\n"
        "3. Pick exactly 1 emoji for each event. Put the actual emoji character "
        "in the \"icon\" field. Use standard Unicode emojis only.\n"
        "4. Respond in {lang}\n"
        "5. Return a JSON array of objects, REORDERED with the most interesting "
        "for children first (space, science, inventions, animals, sports, exploration). "
        "Each object: {{\"id\": <original event number>, \"year\": <year>, "
        "\"text\": \"rewritten text\", \"icon\": \"<single emoji>\", "
        "\"birth\": true/false}}. "
        "Use null instead of an object to skip an event.\n"
        "No markdown, no explanation, just the JSON array.\n\n"
        "Events:\n{events}"
    ).format(
        age=KID_AGE, lang=lang_name, events=events_block,
        violence_rule=(
            "Keep all events, including wars and conflicts. Rephrase for clarity but don't skip anything."
            if KID_AGE >= 10 else
            "If historically very important (end of a major war, major treaty), keep but rephrase gently. "
            "Skip minor violent events by using null. Pick friendly emojis (no weapons)."
        ),
    )

    import urequests
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + AI_API_KEY,
        }
        if AI_PROVIDER == "gemini":
            url = url + "?key=" + AI_API_KEY
            headers.pop("Authorization")

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }

        import json
        resp = urequests.request(
            "POST", url,
            headers=headers,
            data=json.dumps(body).encode("utf-8"),
            timeout=30,
        )

        if resp.status_code != 200:
            err = ""
            try:
                err = resp.text[:100]
            except Exception:
                pass
            resp.close()
            return None, "HTTP {}".format(resp.status_code) + (": " + err if err else "")

        data = resp.json()
        resp.close()

        content = data["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        result = json.loads(content)

        if isinstance(result, list):
            reordered = []
            for item in result:
                if item is None:
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if not text:
                        continue
                    yr = item.get("year")
                    idx = item.get("id")
                    title = _title_by_idx.get(idx, "") if idx else ""
                    is_birth = item.get("birth", False)
                    icon_char = item.get("icon", "")
                    icons = []
                    if icon_char:
                        try:
                            parts = ["{:x}".format(ord(c)) for c in icon_char
                                     if ord(c) > 255 and ord(c) != 0xfe0f and ord(c) != 0xfe0e]
                            cp = "-".join(parts)
                            if cp:
                                icons = [cp]
                        except Exception:
                            pass
                    reordered.append((yr, _capitalize(text), icons, title, is_birth))
                elif isinstance(item, str):
                    reordered.append((None, _capitalize(item), [], "", False))
            if reordered:
                return reordered, None
            return None, "empty result"

        return None, "bad format: " + str(type(result))
    except Exception as e:
        return None, str(e)[:80]


# ─── SD card mount ───────────────────────────────────────────────
SD_DIR = "/sd"
_sd_ok = False
try:
    import machine as _m
    import sdcard as _sdcard
    _sd_spi = _m.SPI(0, sck=_m.Pin(34, _m.Pin.OUT), mosi=_m.Pin(35, _m.Pin.OUT), miso=_m.Pin(36, _m.Pin.OUT))
    _sd = _sdcard.SDCard(_sd_spi, _m.Pin(39))
    try:
        import uos
        uos.mount(_sd, SD_DIR)
    except Exception:
        import os
        os.mount(_sd, SD_DIR)
    _test_dir = SD_DIR + "/_test"
    _test_file = _test_dir + "/t"
    try:
        import os as _os2
        try:
            _os2.mkdir(_test_dir)
        except OSError:
            pass
        with open(_test_file, "w") as _f:
            _f.write("ok")
        with open(_test_file, "r") as _f:
            assert _f.read() == "ok"
        _os2.remove(_test_file)
        _os2.rmdir(_test_dir)
        _sd_ok = True
        print("[sd] mounted", SD_DIR)
    except Exception as _e2:
        print("[sd] write test failed:", _e2)
except Exception as _e:
    print("[sd] not available:", _e)

STORAGE_DIR = SD_DIR if _sd_ok else "."
print("[storage]", STORAGE_DIR)

# ─── Daily cache ─────────────────────────────────────────────────
CACHE_FILE = STORAGE_DIR + "/day_cache.json"


def _cache_key():
    file_hash = 0
    try:
        import hashlib
        h = hashlib.sha256()
        with open("main.py", "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                h.update(chunk)
        file_hash = h.digest()[:4].hex()
    except Exception:
        try:
            import os
            file_hash = os.stat("main.py")[6]
        except Exception:
            pass
    now = time.localtime()
    return "{:04d}-{:02d}-{:02d}-{}".format(now[0], now[1], now[2], file_hash)


def _load_cache():
    try:
        import json
        with open(CACHE_FILE) as f:
            data = json.load(f)
        key = _cache_key()
        if data.get("key") != key:
            print("[cache] stale: got", data.get("key"), "want", key)
            return None
        events = []
        for ev in data.get("events", []):
            events.append((ev.get("year"), ev.get("text", ""), ev.get("icons", []), ev.get("title", ""), ev.get("birth", False)))
        print("[cache] loaded", len(events), "events")
        return events if events else None
    except Exception as e:
        print("[cache] load error:", e)
        return None


def _save_cache(events):
    try:
        import json
        ev_list = []
        for ev in events:
            ev_list.append({
                "year": ev[0], "text": ev[1],
                "icons": ev[2] if len(ev) > 2 else [],
                "title": ev[3] if len(ev) > 3 else "",
                "birth": ev[4] if len(ev) > 4 else False,
            })
        with open(CACHE_FILE, "w") as f:
            json.dump({"key": _cache_key(), "events": ev_list}, f)
        print("[cache] saved", len(ev_list), "events to", CACHE_FILE)
    except Exception as e:
        print("[cache] save error:", e)


# ─── Fetch events from Wikipedia ─────────────────────────────────
def _fetch_events(month, day):
    """Fetch selected events + notable births from Wikipedia."""
    import urequests
    events = []
    base = "https://api.wikimedia.org/feed/v1/wikipedia/{}/onthisday".format(LANGUAGE)
    hdrs = {"User-Agent": "PimoroniEmulator/1.0"}

    # Fetch selected events
    try:
        print("[fetch] selected events...")
        resp = urequests.get("{}/selected/{:02d}/{:02d}".format(base, month, day), headers=hdrs)
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get("selected", [])
            for item in raw:
                text = item.get("text", "")
                year = item.get("year")
                pages = item.get("pages", [])
                title = pages[0].get("title", "").replace("_", " ") if pages else ""
                if text:
                    events.append((year, _capitalize(text), [], title, False))
        resp.close()
    except Exception as e:
        print("[fetch] events error:", e)

    # Fetch notable births (top 5)
    try:
        print("[fetch] births...")
        resp = urequests.get("{}/births/{:02d}/{:02d}".format(base, month, day), headers=hdrs)
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get("births", [])
            for item in raw[:5]:
                text = item.get("text", "")
                year = item.get("year")
                pages = item.get("pages", [])
                title = pages[0].get("title", "").replace("_", " ") if pages else ""
                if text:
                    events.append((year, _capitalize(text), [], title, True))
        resp.close()
    except Exception as e:
        print("[fetch] births error:", e)

    events.sort(key=lambda e: e[0] if e[0] is not None else 9999)
    print("[fetch] total:", len(events), "events")
    return events


# ─── Boot sequence ───────────────────────────────────────────────
try:
    boot_screen("...", 0)

    import machine
    rtc = machine.RTC()
    time_source = "RTC" if _time_is_sane() else None

    # Step 1: WiFi
    wifi_ok = False
    if SKIP_BOOT:
        boot_screen("Skip boot", 2, DIM)
    elif WIFI_SSID:
        boot_screen(_s("wifi_connect") + "...", 0)
        wifi_ok = _connect_wifi()
        if wifi_ok:
            boot_screen(_s("wifi_ok"), 1, OK_PEN)
        else:
            boot_screen(_s("wifi_fail"), 1, ERR_PEN)
    else:
        boot_screen(_s("no_wifi_cfg"), 1, DIM)
    time.sleep(0.3)

    # Step 2: NTP
    if wifi_ok:
        boot_screen(_s("time_sync") + "...", 1)
        import ntptime
        for _attempt in range(3):
            try:
                ntptime.settime()
                utc = time.localtime()
                if utc[0] >= 2025:
                    local = _utc_to_local(utc)
                    rtc.datetime((local[0], local[1], local[2], local[6],
                                  local[3], local[4], local[5], 0))
                    time_source = "NTP"
                    break
            except Exception:
                pass
            boot_screen(_s("time_sync") + "..", 1)
            time.sleep(1)
        if time_source == "NTP":
            boot_screen(_s("time_ok"), 2, OK_PEN)
        else:
            boot_screen(_s("time_fail"), 2, ERR_PEN)
    else:
        if time_source:
            boot_screen(_s("time_ok") + " (RTC)", 2, OK_PEN)
        else:
            boot_screen(_s("time_fail"), 2, ERR_PEN)
    time.sleep(0.3)

    # Step 3-5: Load from cache or fetch + AI + icons
    now = time.localtime()
    today_year = now[0]
    today_month, today_day = now[1], now[2]

    events = _load_cache()
    icon_loader = None

    if events:
        boot_screen("Cache OK !", 4, OK_PEN)
        time.sleep(0.3)
    else:
        events = []
        if wifi_ok:
            boot_screen(_s("fetch") + "...", 2)
            events = _fetch_events(today_month, today_day)

        if events:
            boot_screen("{} events !".format(len(events)), 3, OK_PEN)
        else:
            boot_screen(_s("no_events") if wifi_ok else _s("fetch_fail"), 3, ERR_PEN)
        time.sleep(0.3)

        # Step 4: AI reformulation
        if AI_API_KEY and events:
            rewritten = None
            last_err = None
            for _attempt in range(3):
                boot_screen(_s("ai_rewrite") + "... " + str(_attempt + 1) + "/3", 3)
                rewritten, last_err = _ai_rewrite(events)
                if rewritten:
                    break
                err_msg = last_err or "?"
                if len(err_msg) > 25:
                    err_msg = err_msg[:25]
                boot_screen(err_msg, 3, ERR_PEN)
                time.sleep(1.5)
            if rewritten:
                events = rewritten
                boot_screen(_s("ai_rewrite") + " OK !", 4, OK_PEN)
            else:
                events = [(e[0], _capitalize(e[1]), e[2], e[3] if len(e) > 3 else "", e[4] if len(e) > 4 else False) for e in events]
                boot_screen(last_err or "failed", 4, ERR_PEN)
                time.sleep(2)
        else:
            boot_screen("...", 4)
        time.sleep(0.3)

        if events:
            _save_cache(events)

    # Step 5: Icons
    try:
        from icons import IconLoader
        icon_loader = IconLoader(display, size=28, cache_dir=STORAGE_DIR + "/icon_cache")
        all_tags = set()
        for ev in events:
            if len(ev) > 2:
                for tag in ev[2]:
                    all_tags.add(tag)
        if all_tags and (_is_wifi_connected() or wifi_ok):
            boot_screen("Icons...", 4)
            icon_loader.ensure_many(all_tags)
    except Exception:
        icon_loader = None

    boot_screen(_s("ready"), 5, OK_PEN)
    time.sleep(0.4)

    # ─── Layout constants (adaptive) ────────────────────────────
    MARGIN = 6 if IS_SMALL else (10 if IS_MEDIUM else 20)
    HEADER_H = 20 if IS_SMALL else (28 if IS_MEDIUM else 60)
    FOOTER_H = 0
    TIMESCALE_H = 14 if IS_SMALL else (18 if IS_MEDIUM else 24)
    LINE_H = {1: 12, 2: 20, 3: 30, 4: 40}
    ICON_SZ = 72  # Twemoji native size
    BIRTH_PEN = display.create_pen(255, 180, 100)

    # Pre-create fade background pens (skip on e-ink)
    _FADE_BGS = []
    if not IS_EINK:
        for _fi in range(11):
            _fade = _fi / 10.0
            _FADE_BGS.append(display.create_pen(int(15 * _fade), int(12 * _fade), int(30 * _fade)))

    def word_wrap(text, max_width, scale=2):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if display.measure_text(test, scale=scale, spacing=1) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # ─── Drawing ─────────────────────────────────────────────────
    def draw_header(t):
        date_str = "{} {} {}".format(today_day, _month_name(today_month), today_year)
        display.set_pen(HEADER_BG)
        display.rectangle(0, 0, WIDTH, HEADER_H)

        tw = display.measure_text(date_str, scale=_S_TITLE, spacing=1)
        tx = WIDTH // 2 - tw // 2
        ty = (HEADER_H - 8 * _S_TITLE) // 2
        if not IS_EINK:
            display.set_pen(hsv_pen((t * 0.03) % 1.0, 0.7, 0.6))
            display.text(date_str, tx + 2, ty + 2, -1, scale=_S_TITLE, spacing=1)
        display.set_pen(TEXT)
        display.text(date_str, tx, ty, -1, scale=_S_TITLE, spacing=1)

        line_y = HEADER_H - (2 if IS_SMALL else 3)
        line_w = WIDTH - MARGIN * 2
        if IS_EINK:
            display.set_pen(TEXT)
            display.rectangle(MARGIN, line_y, line_w, 1)
        else:
            for x in range(0, line_w, 4):
                w = min(4, line_w - x)
                display.set_pen(hsv_pen((x / line_w + t * 0.03) % 1.0, 0.8, 0.9))
                display.rectangle(MARGIN + x, line_y, w, 2 if IS_SMALL else 3)

    # Timescale: covers -1000 BC to present (~3026 years total)
    _TS_MIN_YEAR = -1000  # 1000 BC
    _TS_RANGE = today_year - _TS_MIN_YEAR  # e.g. 3026

    def draw_timescale(year, t):
        if year is None:
            return 0
        years_ago = max(0, today_year - year)
        y_top = HEADER_H + 8
        bar_x = MARGIN
        bar_w = WIDTH - MARGIN * 2

        display.set_pen(TEXT)
        display.text(_years_ago_str(years_ago), bar_x, y_top, -1, scale=_S_AGO, spacing=1)

        bar_y = y_top + 8 * _S_AGO + 2
        bar_h = 6

        # Background track
        display.set_pen(TIMESCALE_BG)
        display.rectangle(bar_x, bar_y, bar_w, bar_h)

        # Tick marks at 0, 1000, 2000
        display.set_pen(DIM)
        for mark_year in (0, 1000, 2000):
            if _TS_MIN_YEAR < mark_year < today_year:
                mx = bar_x + int(bar_w * (mark_year - _TS_MIN_YEAR) / _TS_RANGE)
                display.rectangle(mx, bar_y - 2, 1, bar_h + 4)

        # Fill from event year to now (right side)
        event_pos = max(0.0, min(1.0, (year - _TS_MIN_YEAR) / _TS_RANGE))
        fill_start_x = bar_x + int(bar_w * event_pos)
        fill_w = bar_x + bar_w - fill_start_x

        if fill_w > 0:
            for x in range(0, fill_w, 4):
                w = min(4, fill_w - x)
                hue = (x / max(1, bar_w) * 0.7 + t * 0.02) % 1.0
                display.set_pen(hsv_pen(hue, 0.7, 0.8))
                display.rectangle(fill_start_x + x, bar_y + 1, w, bar_h - 2)

        # Marker dot at event position
        display.set_pen(hsv_pen((t * 0.03) % 1.0, 0.8, 1.0))
        display.circle(max(fill_start_x, bar_x + 4), bar_y + bar_h // 2, 4)

        return TIMESCALE_H

    def draw_event(idx, t, alpha=1.0):
        if not events:
            display.set_pen(DIM)
            msg = _s("no_events")
            mw = display.measure_text(msg, scale=_S_TITLE, spacing=1)
            display.text(msg, WIDTH // 2 - mw // 2, HEIGHT // 2 - 16, -1, scale=_S_TITLE, spacing=1)
            return

        ev = events[idx]
        year, text = ev[0], ev[1]
        title = ev[3] if len(ev) > 3 else ""
        is_birth = ev[4] if len(ev) > 4 else False
        body_width = WIDTH - MARGIN * 2

        ts_h = draw_timescale(year, t)
        body_top = HEADER_H + 8 + ts_h + 4
        body_bottom = HEIGHT - FOOTER_H - 6

        y_cursor = body_top
        if year is not None:
            year_str = str(year)
            yw = display.measure_text(year_str, scale=_S_YEAR, spacing=1)
            if IS_EINK:
                display.set_pen(TEXT)
            elif is_birth:
                display.set_pen(BIRTH_PEN)
            else:
                display.set_pen(hsv_pen((t * 0.02 + idx * 0.15) % 1.0, 0.7, alpha))
            display.text(year_str, MARGIN, y_cursor, -1, scale=_S_YEAR, spacing=1)
            if not IS_SMALL:
                pen2 = hsv_pen((t * 0.02 + idx * 0.15 + 0.3) % 1.0, 0.5, 0.6 * alpha)
                display.set_pen(pen2)
                display.rectangle(MARGIN + yw + 10, y_cursor + 8 * _S_YEAR // 2, 40, 3)
            y_cursor += LINE_H[_S_YEAR] + (2 if IS_SMALL else 6)

        if title and not IS_SMALL and not IS_MEDIUM:
            max_title_w = body_width
            truncated_title = title
            while display.measure_text(truncated_title, scale=_S_NAME, spacing=1) > max_title_w and len(truncated_title) > 10:
                truncated_title = truncated_title[:-4] + "..."
            if IS_EINK:
                display.set_pen(TEXT)
            elif is_birth:
                display.set_pen(BIRTH_PEN)
            else:
                display.set_pen(hsv_pen((t * 0.02 + idx * 0.15 + 0.15) % 1.0, 0.5, 0.9 * alpha))
            display.text(truncated_title, MARGIN, y_cursor, -1, scale=_S_NAME, spacing=1)
            y_cursor += LINE_H[_S_NAME] + 2

        available_h = body_bottom - y_cursor
        lines = word_wrap(text, body_width, scale=_S_BODY_BIG)
        line_h = LINE_H[_S_BODY_BIG]
        scale = _S_BODY_BIG
        if len(lines) * line_h > available_h:
            lines = word_wrap(text, body_width, scale=_S_BODY_SM)
            line_h = LINE_H[_S_BODY_SM]
            scale = _S_BODY_SM
        max_lines = max(1, available_h // line_h)
        truncated = len(lines) > max_lines
        if truncated:
            lines = lines[:max_lines]

        display.set_pen(TEXT)
        for line in lines:
            display.text(line, MARGIN, y_cursor, -1, scale=scale, spacing=1)
            y_cursor += line_h
        if truncated:
            display.set_pen(DIM)
            display.text("...", MARGIN + 8, y_cursor, -1, scale=scale, spacing=1)

    def draw_icon(idx):
        if IS_SMALL or IS_MEDIUM or not events or not icon_loader:
            return
        event_icons = events[idx][2] if len(events[idx]) > 2 else []
        if event_icons:
            icon_x = WIDTH - MARGIN - ICON_SZ - 4
            icon_y = HEIGHT - FOOTER_H - ICON_SZ - 4
            icon_loader.draw(event_icons[0], icon_x, icon_y)

    def update_leds(t):
        if not presto:
            return
        for i in range(7):
            hue = (i / 7.0 + t * 0.03) % 1.0
            brightness = 0.12 + math.sin(t * 0.3 + i * 0.9) * 0.06
            presto.set_led_hsv(i, hue, 0.5, max(0.0, brightness))

    # ─── Transition animation ────────────────────────────────────
    def draw_frame(idx, t, fade=1.0):
        """Draw a complete frame. fade: 0.0 = black, 1.0 = fully visible."""
        _set_layer()

        if not IS_EINK and fade < 1.0 and _FADE_BGS:
            fi = max(0, min(10, int(fade * 10)))
            display.set_pen(_FADE_BGS[fi])
        else:
            display.set_pen(BG)
        display.clear()

        if fade > 0.3 or IS_EINK:
            draw_header(t)
            draw_event(idx, t, alpha=fade if not IS_EINK else 1.0)
            draw_icon(idx)
        update_leds(t)
        _update()

    # ─── Button input (non-touch devices) ──────────────────────
    _buttons = {}

    def _check_buttons():
        """Check for button presses (Badger, Inky Frame, Tufty). Returns True if pressed."""
        try:
            from machine import Pin
            # Common button pins across devices
            for pin_num in (12, 13, 14, 15):  # Badger/Inky A/B/C/Up/Down
                if pin_num not in _buttons:
                    _buttons[pin_num] = Pin(pin_num, Pin.IN, Pin.PULL_UP)
                if _buttons[pin_num].value() == 0:
                    return True
        except Exception:
            pass
        return False

    # ─── Main loop ───────────────────────────────────────────────
    if presto:
        presto.set_backlight(NORMAL_BRIGHTNESS)

    current_event = 0
    last_touch = False
    sleeping = False
    needs_redraw = True

    _ticks = time.ticks_ms if hasattr(time, "ticks_ms") else lambda: int(time.time() * 1000)
    t0 = _ticks()
    last_cycle_ms = t0
    last_touch_ms = t0
    last_day = today_day
    last_wifi_retry_ms = t0
    _transition_until = 0
    _prev_event = -1

    while True:
        now_ms = _ticks()
        t = (now_ms - t0) / 1000.0

        # ─── Day change ──────────────────────────────────────
        if int(t) % 3 == 0:
            cur_day = time.localtime()[2]
            if cur_day != last_day:
                try:
                    machine.reset()
                except Exception:
                    last_day = cur_day
                    today_day = cur_day
                    events = []
                    needs_redraw = True

        # ─── WiFi retry (every 60s if disconnected) ──────────
        if WIFI_SSID and not _is_wifi_connected() and not SKIP_BOOT:
            if (now_ms - last_wifi_retry_ms) > 60000:
                last_wifi_retry_ms = now_ms
                _connect_wifi()

        # ─── Night dimming (Presto only) ─────────────────────
        if presto and not sleeping:
            target = DIM_BRIGHTNESS if _is_night() else NORMAL_BRIGHTNESS
            presto.set_backlight(target)

        # ─── Input: touch or buttons ─────────────────────────
        user_input = False
        if HAS_TOUCH:
            touch = presto.touch_a
            touched = touch.touched and not last_touch
            last_touch = touch.touched
            user_input = touched
        else:
            user_input = _check_buttons()

        if user_input:
            last_touch_ms = now_ms
            if sleeping:
                sleeping = False
                if presto:
                    presto.set_backlight(DIM_BRIGHTNESS if _is_night() else NORMAL_BRIGHTNESS)
            elif events:
                _prev_event = current_event
                current_event = (current_event + 1) % len(events)
                last_cycle_ms = now_ms
                needs_redraw = True
                if not IS_EINK:
                    _transition_until = now_ms + 400
            # Debounce buttons
            if not HAS_TOUCH:
                time.sleep(0.2)

        # ─── Sleep on inactivity (Presto only) ───────────────
        if presto and not sleeping and SLEEP_AFTER_SECS > 0:
            if (now_ms - last_touch_ms) > SLEEP_AFTER_SECS * 1000:
                sleeping = True
                presto.set_backlight(SLEEP_BRIGHTNESS)

        # ─── Auto-cycle ─────────────────────────────────────
        if events and AUTO_CYCLE_SECS > 0 and not sleeping:
            elapsed = (now_ms - last_cycle_ms) / 1000.0
            if elapsed >= AUTO_CYCLE_SECS:
                _prev_event = current_event
                current_event = (current_event + 1) % len(events)
                last_cycle_ms = now_ms
                needs_redraw = True
                if not IS_EINK:
                    _transition_until = now_ms + 400

        # ─── Draw ────────────────────────────────────────────
        if IS_EINK:
            # E-ink: only redraw when content changes
            if needs_redraw:
                draw_frame(current_event, t)
                needs_redraw = False
            time.sleep(0.1)
        elif _transition_until > now_ms:
            progress = 1.0 - ((_transition_until - now_ms) / 400.0)
            if progress < 0.5:
                fade = 1.0 - (progress * 2.0)
                draw_frame(_prev_event if _prev_event >= 0 else current_event, t, fade)
            else:
                fade = (progress - 0.5) * 2.0
                draw_frame(current_event, t, fade)
        else:
            draw_frame(current_event, t)
            time.sleep(0.05)
except Exception as e:
    import sys
    try:
        sys.print_exception(e)
    except Exception:
        pass
    _show_crash(e, e)
