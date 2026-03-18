"""Network, data fetching, AI rewrite, and caching."""

import time
from config import (
    WIFI_SSID, WIFI_PASSWORD, AI_API_KEY, AI_PROVIDER, AI_MODEL, AI_DEFAULTS,
    KID_AGE, LANGUAGE, LANG_NAMES, capitalize,
)

# ─── WiFi ────────────────────────────────────────────────────────
_wlan = None


def connect_wifi():
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


def is_wifi_connected():
    return _wlan is not None and _wlan.isconnected()


# ─── Wikipedia fetch ─────────────────────────────────────────────
def fetch_events(month, day):
    """Fetch selected events + notable births. Returns list of 5-tuples:
    (year, text, icons, title, is_birth)"""
    import urequests
    events = []
    base = "https://api.wikimedia.org/feed/v1/wikipedia/{}/onthisday".format(LANGUAGE)
    hdrs = {"User-Agent": "PimoroniEmulator/1.0"}

    for endpoint, is_birth, limit in [("selected", False, None), ("births", True, 5)]:
        try:
            print("[fetch]", endpoint + "...")
            resp = urequests.get("{}/{}/{:02d}/{:02d}".format(base, endpoint, month, day), headers=hdrs)
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get(endpoint, [])
                if limit:
                    raw = raw[:limit]
                for item in raw:
                    text = item.get("text", "")
                    year = item.get("year")
                    pages = item.get("pages", [])
                    title = pages[0].get("title", "").replace("_", " ") if pages else ""
                    if text:
                        events.append((year, capitalize(text), [], title, is_birth))
            resp.close()
        except Exception as e:
            print("[fetch] error:", e)

    events.sort(key=lambda e: e[0] if e[0] is not None else 9999)
    print("[fetch] total:", len(events))
    return events


# ─── AI rewrite ──────────────────────────────────────────────────
def _emoji_to_codepoint(char):
    """Convert an emoji character to a Twemoji-compatible codepoint string."""
    try:
        parts = ["{:x}".format(ord(c)) for c in char
                 if ord(c) > 255 and ord(c) != 0xfe0f and ord(c) != 0xfe0e]
        return "-".join(parts) if parts else ""
    except Exception:
        return ""


def ai_rewrite(events_list):
    """Rewrite events for kids. Returns (events, error_msg) tuple."""
    if not AI_API_KEY or not events_list:
        return None, "no API key"
    provider = AI_DEFAULTS.get(AI_PROVIDER)
    if not provider:
        return None, "unknown provider"

    url = provider["url"]
    model = AI_MODEL or provider["model"]
    lang_name = LANG_NAMES.get(LANGUAGE, "English")

    title_by_idx = {}
    for i, ev in enumerate(events_list):
        if len(ev) > 3 and ev[3]:
            title_by_idx[i + 1] = ev[3]

    lines = []
    for i, ev in enumerate(events_list):
        is_birth = ev[4] if len(ev) > 4 else False
        tag = "[BIRTH {}]".format(ev[0] or "?") if is_birth else "[{}]".format(ev[0] or "?")
        lines.append("{}. {} {}".format(i + 1, tag, ev[1]))

    violence = (
        "Keep all events, including wars. Rephrase for clarity."
        if KID_AGE >= 10 else
        "Keep only historically important violent events, rephrase gently. Skip minor ones (null)."
    )

    prompt = (
        "You are preparing a daily \"On This Day\" display for a {age}-year-old child. "
        "Small screen, bitmap font (ASCII only). We can show 1 emoji icon per event.\n\n"
        "Rules:\n"
        "1. REWRITE for a {age}-year-old: keep real names/facts, simpler sentences, "
        "1-2 short sentences, ASCII only, capitalize first letter.\n"
        "   For BIRTH entries: say who and why famous.\n"
        "2. Violence: {violence}\n"
        "3. Pick 1 Unicode emoji per event (\"icon\" field).\n"
        "4. Respond in {lang}.\n"
        "5. Return JSON array, REORDERED (most interesting for kids first). "
        "Each: {{\"id\": <N>, \"year\": <Y>, \"text\": \"...\", \"icon\": \"<emoji>\", \"birth\": bool}}. "
        "null to skip.\n\n"
        "Events:\n{events}"
    ).format(age=KID_AGE, lang=lang_name, violence=violence, events="\n".join(lines))

    import urequests
    import json
    try:
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + AI_API_KEY}
        if AI_PROVIDER == "gemini":
            url = url + "?key=" + AI_API_KEY
            headers.pop("Authorization")

        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        resp = urequests.request("POST", url, headers=headers,
                                 data=json.dumps(body).encode("utf-8"), timeout=30)

        if resp.status_code != 200:
            err = resp.text[:100] if hasattr(resp, 'text') else ""
            resp.close()
            return None, "HTTP {}".format(resp.status_code) + (": " + err if err else "")

        data = resp.json()
        resp.close()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)

        if not isinstance(result, list):
            return None, "bad format"

        reordered = []
        for item in result:
            if item is None or not isinstance(item, dict):
                continue
            text = item.get("text")
            if not text:
                continue
            yr = item.get("year")
            idx = item.get("id")
            title = title_by_idx.get(idx, "") if idx else ""
            icons = []
            cp = _emoji_to_codepoint(item.get("icon", ""))
            if cp:
                icons = [cp]
            reordered.append((yr, capitalize(text), icons, title, item.get("birth", False)))
        return (reordered, None) if reordered else (None, "empty result")
    except Exception as e:
        return None, str(e)[:80]


# ─── Cache ───────────────────────────────────────────────────────
def cache_key():
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


def load_cache(cache_file):
    try:
        import json
        with open(cache_file) as f:
            data = json.load(f)
        key = cache_key()
        if data.get("key") != key:
            print("[cache] stale:", data.get("key"), "!=", key)
            return None
        events = []
        for ev in data.get("events", []):
            events.append((ev.get("year"), ev.get("text", ""), ev.get("icons", []),
                           ev.get("title", ""), ev.get("birth", False)))
        print("[cache] loaded", len(events), "events")
        return events if events else None
    except Exception as e:
        print("[cache] load:", e)
        return None


def save_cache(cache_file, events):
    try:
        import json
        ev_list = [{"year": e[0], "text": e[1], "icons": e[2] if len(e) > 2 else [],
                     "title": e[3] if len(e) > 3 else "", "birth": e[4] if len(e) > 4 else False}
                    for e in events]
        with open(cache_file, "w") as f:
            json.dump({"key": cache_key(), "events": ev_list}, f)
        print("[cache] saved", len(ev_list), "events")
    except Exception as e:
        print("[cache] save error:", e)
