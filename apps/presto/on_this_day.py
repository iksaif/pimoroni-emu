"""On This Day — today's date and a historical event from Wikipedia.

Fetches curated events from Wikipedia's "On This Day" API and cycles
through them. Touch the screen (Presto) or wait to see the next event.
Filters out violent/war content to keep it kid-friendly.

Optionally uses a free AI API (Groq, Gemini, or Mistral) to reformulate
events for young children and add emojis.

Works on Presto (primary) and other PicoGraphics devices (Tufty, Inky Frame,
Badger). For non-Presto devices, change the fallback import below.

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
# Also check os.environ on desktop (MicroPython doesn't have it)
try:
    import os
    for _k in ("WIFI_SSID", "WIFI_PASSWORD", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL"):
        _v = os.environ.get(_k)
        if _v is not None:
            _env.setdefault(_k, _v)
except (ImportError, AttributeError):
    pass

# ─── Configuration ───────────────────────────────────────────────
# Values are read from .env file, os.environ, or defaults below.
# On real hardware, create a .env file on the device with your settings.
LANGUAGE = "fr"                                       # Wikipedia language
WIFI_SSID = _env.get("WIFI_SSID", "")                # WiFi SSID
WIFI_PASSWORD = _env.get("WIFI_PASSWORD", "")         # WiFi password
UTC_OFFSET_WINTER = 1                                 # UTC offset (CET = 1)
UTC_OFFSET_SUMMER = 2                                 # UTC offset (CEST = 2)
EVENT_CATEGORY = "selected"                           # selected, events, births, deaths
AUTO_CYCLE_SECS = 15                                  # Auto-cycle interval
KID_FRIENDLY = True                                   # Filter violent content
DARK_THEME = True                                     # True for TFT, False for e-ink

# AI reformulation (optional — needs API key in .env)
# Supported: "groq", "gemini", "mistral"
AI_PROVIDER = _env.get("AI_PROVIDER", "groq")
AI_API_KEY = _env.get("AI_API_KEY", "")
AI_MODEL = _env.get("AI_MODEL", "")
KID_AGE = 10                                          # Target age
SKIP_BOOT = _env.get("SKIP_BOOT", "") != ""           # Skip WiFi/NTP/fetch (use cache only)
# ─────────────────────────────────────────────────────────────────

# Provider defaults
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

# Keywords to filter out when KID_FRIENDLY is True (lowercase, multi-language)
_BLOCKLIST = [
    # English
    "war", "massacre", "assassin", "murder", "genocide", "terrorist",
    "terrorism", "bombing", "execution", "killed", "killing", "attack",
    "shooting", "slaughter", "torture", "holocaust",
    # French
    "guerre", "massacre", "assassin", "meurtre", "genocide", "terroris",
    "attentat", "execution", "bombe", "tuer", "tuerie", "fusill",
    "torture",
    # German
    "krieg", "mord", "anschlag", "hinrichtung", "massaker",
    # Spanish
    "guerra", "asesin", "masacre", "atentado", "ejecucion",
]

# Month names by language
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

# "X years ago" format by language
_AGO_FMT = {
    "fr": "il y a {} ans",
    "en": "{} years ago",
    "de": "vor {} Jahren",
    "es": "hace {} anos",
    "it": "{} anni fa",
    "pt": "ha {} anos",
}

# UI strings by language
_STRINGS = {
    "fr": {
        "title": "Ce jour dans l'histoire",
        "wifi_connect": "WiFi",
        "wifi_ok": "WiFi OK !",
        "wifi_fail": "WiFi echoue",
        "no_wifi_cfg": "WiFi non configure",
        "time_sync": "Heure",
        "time_ok": "Heure OK !",
        "time_fail": "Pas d'heure",
        "fetch": "Chargement",
        "fetch_ok": "Pret !",
        "fetch_fail": "Erreur chargement",
        "no_events": "Aucun evenement",
        "network_err": "Erreur reseau",
        "ready": "C'est parti !",
        "ai_rewrite": "Simplification",
    },
    "en": {
        "title": "On This Day",
        "wifi_connect": "WiFi",
        "wifi_ok": "WiFi OK!",
        "wifi_fail": "WiFi failed",
        "no_wifi_cfg": "WiFi not set",
        "time_sync": "Time sync",
        "time_ok": "Time OK!",
        "time_fail": "No time source",
        "fetch": "Fetching",
        "fetch_ok": "Ready!",
        "fetch_fail": "Fetch failed",
        "no_events": "No events found",
        "network_err": "Network error",
        "ready": "Ready!",
        "ai_rewrite": "Simplifying",
    },
}

# Language names for AI prompt
_LANG_NAMES = {
    "fr": "French", "en": "English", "de": "German",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese",
}


def _s(key):
    strings = _STRINGS.get(LANGUAGE, _STRINGS.get("en", {}))
    return strings.get(key, _STRINGS.get("en", {}).get(key, key))


def _month_name(month_1indexed):
    months = _MONTHS.get(LANGUAGE, _MONTHS.get("en"))
    return months[month_1indexed - 1]


def _years_ago_str(years):
    fmt = _AGO_FMT.get(LANGUAGE, _AGO_FMT["en"])
    return fmt.format(years)


def _is_kid_safe(text):
    if not KID_FRIENDLY:
        return True
    lower = text.lower()
    for word in _BLOCKLIST:
        if word in lower:
            return False
    return True


# ─── Device init ─────────────────────────────────────────────────
presto = None
try:
    from presto import Presto
    presto = Presto(full_res=True)
    display = presto.display
except ImportError:
    from picographics import PicoGraphics, DISPLAY_TUFTY_2350
    display = PicoGraphics(display=DISPLAY_TUFTY_2350)

WIDTH, HEIGHT = display.get_bounds()


def _show_crash(err_type, err_msg):
    """Show an error on screen. Works even if theme/fonts aren't set up yet."""
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
        # Word-wrap the error message manually
        msg = str(err_msg)
        y = 70
        chunk = 40  # chars per line at scale=2
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
    # Stay on crash screen
    while True:
        time.sleep(1)


# ─── HSV pen helper with cache ───────────────────────────────────
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


# ─── Simple PRNG ─────────────────────────────────────────────────
_seed = 12345


def rng():
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed


def rng_range(a, b):
    return a + rng() % (b - a + 1)


def rng_float():
    return (rng() & 0xFFFF) / 65536.0


# ─── Twinkling stars ─────────────────────────────────────────────
class Star:
    __slots__ = ("x", "y", "hue", "phase", "speed")

    def __init__(self):
        self.x = rng_range(5, WIDTH - 5)
        self.y = rng_range(40, HEIGHT - 30)
        self.hue = rng_float()
        self.phase = rng_float() * 6.28
        self.speed = 0.4 + rng_float() * 0.8

    def draw(self, t):
        brightness = (math.sin(self.phase + t * self.speed) + 1.0) * 0.5
        if brightness < 0.35:
            return
        pen = hsv_pen(self.hue + t * 0.01, 0.4, brightness * 0.5)
        display.set_pen(pen)
        s = 1 if brightness < 0.7 else 2
        display.rectangle(self.x, self.y, s, s)


stars = [Star() for _ in range(12)]


# ─── Boot screen ─────────────────────────────────────────────────
_BOOT_STEPS = 5  # init, wifi, time, fetch, ai


def boot_screen(message, step, color=None):
    cx = WIDTH // 2

    if presto:
        display.set_layer(0)
    display.set_pen(BG)
    display.clear()

    # Title
    title = _s("title")
    tw = display.measure_text(title, scale=4, spacing=1)
    display.set_pen(TEXT)
    display.text(title, cx - tw // 2, HEIGHT // 4 - 20, -1, scale=4, spacing=1)

    # Decorative dots (rainbow)
    dot_y = HEIGHT // 4 + 25
    for i in range(5):
        dx = (i - 2) * 20
        pen = hsv_pen(i / 5.0, 0.8, 0.85)
        display.set_pen(pen)
        display.circle(cx + dx, dot_y, 3)

    # Progress bar
    bar_w = int(WIDTH * 0.7)
    bar_h = 10
    bx = cx - bar_w // 2
    by = HEIGHT // 2 - 5

    display.set_pen(DIM)
    display.rectangle(bx, by, bar_w, bar_h)

    fill = int(bar_w * step / _BOOT_STEPS)
    if fill > 0:
        for x in range(0, fill, 4):
            w = min(4, fill - x)
            pen = hsv_pen(x / bar_w, 0.8, 0.9)
            display.set_pen(pen)
            display.rectangle(bx + x, by + 1, w, bar_h - 2)

    for i in range(_BOOT_STEPS):
        dot_x = bx + int(bar_w * (i + 1) / _BOOT_STEPS)
        if i < step:
            pen = hsv_pen(i / _BOOT_STEPS, 0.7, 0.9)
            display.set_pen(pen)
        else:
            display.set_pen(DIM)
        display.circle(dot_x, by + bar_h // 2, 4)

    display.set_pen(color if color else TEXT)
    sw = display.measure_text(message, scale=3, spacing=1)
    display.text(message, cx - sw // 2, HEIGHT // 2 + 25, -1, scale=3, spacing=1)

    _update()


# ─── Time helpers ────────────────────────────────────────────────
def _get_utc_offset():
    month = time.localtime()[1]
    if 4 <= month <= 9:
        return UTC_OFFSET_SUMMER
    return UTC_OFFSET_WINTER


def _utc_to_local(utc):
    offset = _get_utc_offset()
    local_secs = time.mktime(utc) + offset * 3600
    return time.localtime(local_secs)


def _time_is_sane():
    return time.localtime()[0] >= 2025


# ─── AI reformulation ───────────────────────────────────────────
def _ai_rewrite(events_list):
    """Rewrite events for kids using an AI API. Returns list of new texts."""
    if not AI_API_KEY or not events_list:
        return None

    provider = _AI_DEFAULTS.get(AI_PROVIDER)
    if not provider:
        return None

    url = provider["url"]
    model = AI_MODEL or provider["model"]
    lang_name = _LANG_NAMES.get(LANGUAGE, "English")

    # Build year->title lookup from original events
    _title_by_year = {}
    for ev in events_list:
        if ev[0] is not None and len(ev) > 3 and ev[3]:
            _title_by_year[ev[0]] = ev[3]

    # Build a single prompt with all events
    event_lines = []
    for i, ev in enumerate(events_list):
        year, text = ev[0], ev[1]
        event_lines.append("{}. [{}] {}".format(i + 1, year or "?", text))
    events_block = "\n".join(event_lines)

    prompt = (
        "You are preparing a daily \"On This Day\" display for a {age}-year-old child. "
        "The display uses a small screen with a bitmap font (ASCII only, no Unicode/emojis in text). "
        "But we CAN display a small emoji icon next to each event.\n\n"
        "Below are historical events that happened on this date.\n\n"
        "Your job:\n"
        "1. REWRITE each event so a {age}-year-old can understand, but:\n"
        "   - KEEP real names of people, places, and things\n"
        "   - KEEP specific facts (numbers, names, places)\n"
        "   - Just use simpler sentence structure\n"
        "   - 1-2 short sentences per event\n"
        "   - Text must be ASCII only (no emojis, no special chars)\n"
        "2. For violent/war events: if historically very important "
        "(end of a major war, major treaty), keep but rephrase gently. "
        "Skip minor violent events by using null.\n"
        "3. Pick exactly 1 emoji for each event. Put the actual emoji character "
        "in the \"icon\" field (e.g. \"icon\": \"\\ud83d\\ude80\" for rocket). "
        "Use standard Unicode emojis only.\n"
        "4. Respond in {lang}\n"
        "5. Return a JSON array of objects, REORDERED with the most interesting "
        "for children first (space, science, inventions, animals, sports, exploration). "
        "Each object: {{\"year\": <original year>, \"text\": \"rewritten text\", "
        "\"icon\": \"<single emoji>\"}}. "
        "Use null instead of an object to skip an event.\n"
        "No markdown, no explanation, just the JSON array.\n\n"
        "Events:\n{events}"
    ).format(age=KID_AGE, lang=lang_name, events=events_block)

    import urequests
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + AI_API_KEY,
        }
        # Gemini uses key param instead of Bearer token
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
        # Strip markdown code fences if present
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
                    title = _title_by_year.get(yr, "")
                    # Convert emoji char to codepoint for Twemoji
                    icon_char = item.get("icon", "")
                    icons = []
                    if icon_char:
                        try:
                            # Filter out variation selectors (fe0f, fe0e) that Twemoji doesn't use in filenames
                            parts = ["{:x}".format(ord(c)) for c in icon_char if ord(c) > 255 and ord(c) != 0xfe0f and ord(c) != 0xfe0e]
                            cp = "-".join(parts)
                            if cp:
                                icons = [cp]
                        except Exception:
                            pass
                    reordered.append((yr, text, icons, title))
                elif isinstance(item, str):
                    reordered.append((None, item, [], ""))
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
    # Verify SD is actually writable (create a subdir and file)
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
    """Build a cache key from today's date + hash of main.py content."""
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
    """Load cached events if cache key matches. Returns list of tuples or None."""
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
            events.append((ev.get("year"), ev.get("text", ""), ev.get("icons", []), ev.get("title", "")))
        print("[cache] loaded", len(events), "events")
        return events if events else None
    except Exception as e:
        print("[cache] load error:", e)
        return None


def _save_cache(events):
    """Save events to cache file."""
    try:
        import json
        ev_list = []
        for ev in events:
            ev_list.append({"year": ev[0], "text": ev[1], "icons": ev[2] if len(ev) > 2 else [], "title": ev[3] if len(ev) > 3 else ""})
        with open(CACHE_FILE, "w") as f:
            json.dump({"key": _cache_key(), "events": ev_list}, f)
        print("[cache] saved", len(ev_list), "events to", CACHE_FILE)
    except Exception as e:
        print("[cache] save error:", e)


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
        try:
            import network
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            for _i in range(100):
                if wlan.isconnected():
                    break
                if _i % 10 == 0:
                    dots = "." * ((_i // 10) % 4 + 1)
                    boot_screen(_s("wifi_connect") + dots, 0)
                time.sleep(0.1)
            wifi_ok = wlan.isconnected()
            if wifi_ok:
                boot_screen(_s("wifi_ok"), 1, OK_PEN)
            else:
                boot_screen(_s("wifi_fail"), 1, ERR_PEN)
        except Exception:
            boot_screen(_s("network_err"), 1, ERR_PEN)
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
        # Step 3: Fetch events from Wikipedia
        events = []
        if wifi_ok:
            boot_screen(_s("fetch") + "...", 2)
            api_url = (
                "https://api.wikimedia.org/feed/v1/wikipedia/{}/onthisday/{}/{:02d}/{:02d}"
                .format(LANGUAGE, EVENT_CATEGORY, today_month, today_day)
            )
            try:
                import urequests
                resp = urequests.get(api_url, headers={"User-Agent": "PimoroniEmulator/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        raw = (data.get(EVENT_CATEGORY)
                               or data.get("selected")
                               or data.get("events")
                               or [])
                    elif isinstance(data, list):
                        raw = data
                    else:
                        raw = []
                    for item in raw:
                        text = item.get("text", "")
                        year = item.get("year")
                        pages = item.get("pages", [])
                        title = pages[0].get("title", "").replace("_", " ") if pages else ""
                        if text and (AI_API_KEY or _is_kid_safe(text)):
                            events.append((year, text, [], title))
                    events.sort(key=lambda e: e[0] if e[0] is not None else 9999)
                resp.close()
            except Exception:
                pass

        if events:
            boot_screen("{} events !".format(len(events)), 3, OK_PEN)
        else:
            boot_screen(_s("no_events") if wifi_ok else _s("fetch_fail"), 3, ERR_PEN)
        time.sleep(0.3)

        # Step 4: AI reformulation (optional, with retries)
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
                boot_screen(last_err or "failed", 4, ERR_PEN)
                time.sleep(2)
        else:
            boot_screen("...", 4)
        time.sleep(0.3)

        # Save to cache for next boot
        if events:
            _save_cache(events)

    # Step 5: Pre-download icons (always, cache may not have them on disk)
    if wifi_ok:
        try:
            from icons import IconLoader
            icon_loader = IconLoader(display, size=28, cache_dir=STORAGE_DIR + "/icon_cache")
            all_tags = set()
            for ev in events:
                if len(ev) > 2:
                    for tag in ev[2]:
                        all_tags.add(tag)
            if all_tags:
                boot_screen("Icons...", 4)
                icon_loader.ensure_many(all_tags)
        except Exception:
            icon_loader = None
    else:
        # Try to load icon loader even offline (icons may be cached)
        try:
            from icons import IconLoader
            icon_loader = IconLoader(display, size=28, cache_dir=STORAGE_DIR + "/icon_cache")
        except Exception:
            icon_loader = None

    boot_screen(_s("ready"), 5, OK_PEN)
    time.sleep(0.4)


    # ─── Text layout ────────────────────────────────────────────────
    MARGIN = 20
    HEADER_H = 60
    FOOTER_H = 40
    TIMESCALE_H = 24  # height for the "X years ago" bar
    LINE_H_S4 = 40
    LINE_H_S3 = 30
    LINE_H_S2 = 20


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


    # ─── Drawing ─────────────────────────────────────────────────────
    def draw_header(t):
        date_str = "{} {} {}".format(today_day, _month_name(today_month), today_year)

        display.set_pen(HEADER_BG)
        display.rectangle(0, 0, WIDTH, HEADER_H)

        tw = display.measure_text(date_str, scale=4, spacing=1)
        tx = WIDTH // 2 - tw // 2

        # Colorful shadow
        pen = hsv_pen((t * 0.03) % 1.0, 0.7, 0.6)
        display.set_pen(pen)
        display.text(date_str, tx + 2, 12, -1, scale=4, spacing=1)

        display.set_pen(TEXT)
        display.text(date_str, tx, 10, -1, scale=4, spacing=1)

        # Rainbow accent line
        line_y = HEADER_H - 3
        line_w = WIDTH - MARGIN * 2
        for x in range(0, line_w, 4):
            w = min(4, line_w - x)
            pen = hsv_pen((x / line_w + t * 0.03) % 1.0, 0.8, 0.9)
            display.set_pen(pen)
            display.rectangle(MARGIN + x, line_y, w, 3)


    def draw_timescale(year, t):
        """Draw a visual time scale showing how far in the past the event is."""
        if year is None:
            return 0  # no extra height used

        years_ago = today_year - year
        if years_ago < 0:
            years_ago = 0

        y_top = HEADER_H + 8
        bar_x = MARGIN
        bar_w = WIDTH - MARGIN * 2

        # "il y a X ans" label
        ago_str = _years_ago_str(years_ago)
        display.set_pen(TEXT)
        display.text(ago_str, bar_x, y_top, -1, scale=2, spacing=1)

        # Time bar: represents 0-2000 years, with the event marked
        bar_y = y_top + 16
        bar_h = 6

        # Background track
        display.set_pen(TIMESCALE_BG)
        display.rectangle(bar_x, bar_y, bar_w, bar_h)

        # Fill from right (now) to left (past), proportional to age
        max_years = 2000
        ratio = min(1.0, years_ago / max_years)
        fill_w = max(4, int(bar_w * ratio))
        fill_start = bar_x + bar_w - fill_w

        # Rainbow gradient fill (right=now, left=past)
        for x in range(0, fill_w, 4):
            w = min(4, fill_w - x)
            hue = (x / bar_w * 0.7 + t * 0.02) % 1.0
            pen = hsv_pen(hue, 0.7, 0.8)
            display.set_pen(pen)
            display.rectangle(fill_start + x, bar_y + 1, w, bar_h - 2)

        # Marker dot at the event position (left end of fill)
        pen = hsv_pen((t * 0.03) % 1.0, 0.8, 1.0)
        display.set_pen(pen)
        display.circle(max(fill_start, bar_x + 4), bar_y + bar_h // 2, 4)

        return TIMESCALE_H


    def draw_event(idx, t):
        if not events:
            display.set_pen(DIM)
            msg = _s("no_events")
            mw = display.measure_text(msg, scale=4, spacing=1)
            display.text(msg, WIDTH // 2 - mw // 2, HEIGHT // 2 - 16, -1, scale=4, spacing=1)
            return

        ev = events[idx]
        year, text = ev[0], ev[1]
        event_icons = ev[2] if len(ev) > 2 else []
        title = ev[3] if len(ev) > 3 else ""
        body_width = WIDTH - MARGIN * 2

        # Time scale
        ts_h = draw_timescale(year, t)
        body_top = HEADER_H + 8 + ts_h + 4
        body_bottom = HEIGHT - FOOTER_H - 6

        # Year with color cycling
        y_cursor = body_top
        if year is not None:
            year_str = str(year)
            yw = display.measure_text(year_str, scale=4, spacing=1)

            pen = hsv_pen((t * 0.02 + idx * 0.15) % 1.0, 0.7, 1.0)
            display.set_pen(pen)
            display.text(year_str, MARGIN, y_cursor, -1, scale=4, spacing=1)

            # Decorative bar after year
            pen2 = hsv_pen((t * 0.02 + idx * 0.15 + 0.3) % 1.0, 0.5, 0.6)
            display.set_pen(pen2)
            display.rectangle(MARGIN + yw + 10, y_cursor + 16, 40, 3)

            y_cursor += LINE_H_S4 + 6

        # Event title (original Wikipedia article name)
        if title:
            pen = hsv_pen((t * 0.02 + idx * 0.15 + 0.15) % 1.0, 0.5, 0.9)
            display.set_pen(pen)
            display.text(title, MARGIN, y_cursor, -1, scale=2, spacing=1)
            y_cursor += LINE_H_S2 + 2

        # Event text — try scale=3 first, then scale=2
        available_h = body_bottom - y_cursor

        lines = word_wrap(text, body_width, scale=3)
        line_h = LINE_H_S3
        scale = 3

        if len(lines) * line_h > available_h:
            lines = word_wrap(text, body_width, scale=2)
            line_h = LINE_H_S2
            scale = 2

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


    def draw_footer(idx, t):
        if not events:
            return

        footer_y = HEIGHT - FOOTER_H

        # Rainbow separator
        line_w = WIDTH - MARGIN * 2
        for x in range(0, line_w, 4):
            w = min(4, line_w - x)
            pen = hsv_pen((x / line_w + t * 0.03 + 0.5) % 1.0, 0.6, 0.5)
            display.set_pen(pen)
            display.rectangle(MARGIN + x, footer_y, w, 2)

        # Navigation arrows
        pen = hsv_pen((t * 0.05) % 1.0, 0.6, 0.9)
        display.set_pen(pen)
        ax = MARGIN + 6
        ay = footer_y + 20
        display.triangle(ax, ay, ax + 12, ay - 10, ax + 12, ay + 10)
        rx = WIDTH - MARGIN - 6
        display.triangle(rx, ay, rx - 12, ay - 10, rx - 12, ay + 10)

        # Counter
        counter = "{}/{}".format(idx + 1, len(events))
        display.set_pen(TEXT)
        cw = display.measure_text(counter, scale=2, spacing=1)
        display.text(counter, rx - 16 - cw, footer_y + 10, -1, scale=2, spacing=1)


    # Icon is 72px from Twemoji (rendered at native size)
    ICON_SZ = 72

    def draw_icon(idx):
        """Draw a single icon in the bottom-right of the text area."""
        if not events or not icon_loader:
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


    # ─── Main loop ───────────────────────────────────────────────────
    if presto:
        presto.set_backlight(1.0)

    current_event = 0
    last_touch = False

    t0 = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
    last_cycle_ms = t0

    while True:
        now_ms = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
        t = (now_ms - t0) / 1000.0

        # Input
        if presto:
            touch = presto.touch_a
            touched = touch.touched and not last_touch
            last_touch = touch.touched
        else:
            touched = False

        if events and touched:
            current_event = (current_event + 1) % len(events)
            last_cycle_ms = now_ms
            pass

        if events and AUTO_CYCLE_SECS > 0:
            elapsed = (now_ms - last_cycle_ms) / 1000.0
            if elapsed >= AUTO_CYCLE_SECS:
                current_event = (current_event + 1) % len(events)
                last_cycle_ms = now_ms

        # Draw
        if presto:
            display.set_layer(0)
        display.set_pen(BG)
        display.clear()

        for s in stars:
            s.draw(t)

        draw_header(t)
        draw_event(current_event, t)
        draw_icon(current_event)
        draw_footer(current_event, t)
        update_leds(t)

        _update()
        time.sleep(0.05)
except Exception as e:
    import sys
    try:
        sys.print_exception(e)
    except Exception:
        pass
    _show_crash(e, e)
