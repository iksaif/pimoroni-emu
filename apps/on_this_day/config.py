"""Configuration, .env loading, and i18n strings."""

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

AI_PROVIDER = _env.get("AI_PROVIDER", "groq")
AI_API_KEY = _env.get("AI_API_KEY", "")
AI_MODEL = _env.get("AI_MODEL", "")
KID_AGE = 10

DIM_HOUR_START = 20
DIM_HOUR_END = 7
DIM_BRIGHTNESS = 0.15
NORMAL_BRIGHTNESS = 1.0
SLEEP_AFTER_SECS = 300
SLEEP_BRIGHTNESS = 0.02

SKIP_BOOT = _env.get("SKIP_BOOT", "") != ""

AI_DEFAULTS = {
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "model": "llama-3.3-70b-versatile"},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "model": "gemini-2.0-flash"},
    "mistral": {"url": "https://api.mistral.ai/v1/chat/completions", "model": "mistral-small-latest"},
}

# ─── I18n ────────────────────────────────────────────────────────
MONTHS = {
    "fr": ["janvier", "fevrier", "mars", "avril", "mai", "juin",
           "juillet", "aout", "septembre", "octobre", "novembre", "decembre"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "de": ["Januar", "Februar", "Marz", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
}

AGO_FMT = {
    "fr": "il y a {} ans", "en": "{} years ago",
    "de": "vor {} Jahren", "es": "hace {} anos",
}

STRINGS = {
    "fr": {
        "title": "Ce jour dans l'histoire",
        "wifi_connect": "WiFi", "wifi_ok": "WiFi OK !",
        "wifi_fail": "WiFi echoue", "no_wifi_cfg": "WiFi non configure",
        "time_sync": "Heure", "time_ok": "Heure OK !",
        "time_fail": "Pas d'heure",
        "fetch": "Chargement", "fetch_fail": "Erreur chargement",
        "no_events": "Aucun evenement", "network_err": "Erreur reseau",
        "ready": "C'est parti !", "ai_rewrite": "Simplification",
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
    },
}

LANG_NAMES = {"fr": "French", "en": "English", "de": "German", "es": "Spanish"}


def s(key):
    """Get localized UI string."""
    strings = STRINGS.get(LANGUAGE, STRINGS.get("en", {}))
    return strings.get(key, STRINGS.get("en", {}).get(key, key))


def month_name(m):
    return MONTHS.get(LANGUAGE, MONTHS.get("en"))[m - 1]


def years_ago_str(y):
    return AGO_FMT.get(LANGUAGE, AGO_FMT["en"]).format(y)


def capitalize(text):
    if text and text[0].islower():
        return text[0].upper() + text[1:]
    return text


def get_utc_offset():
    month = time.localtime()[1]
    return UTC_OFFSET_SUMMER if 4 <= month <= 9 else UTC_OFFSET_WINTER


def utc_to_local(utc):
    return time.localtime(time.mktime(utc) + get_utc_offset() * 3600)


def is_night():
    hour = time.localtime()[3]
    if DIM_HOUR_START > DIM_HOUR_END:
        return hour >= DIM_HOUR_START or hour < DIM_HOUR_END
    return DIM_HOUR_START <= hour < DIM_HOUR_END
