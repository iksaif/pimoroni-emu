"""Status classification thresholds for the WiFi Health Monitor.

Three profiles (loose / normal / strict) define the bands at which each
metric flips from ok to warn to down. See the design doc for the source
of these numbers.
"""


PROFILES = {
    "LOOSE": {
        "latency":  {"ok": 100,  "warn": 250},   # ms
        "loss":     {"ok": 3,    "warn": 10},    # %
        "jitter":   {"ok": 15,   "warn": 40},    # ms
        "dns":      {"ok": 100,  "warn": 400},   # ms
        "rssi":     {"ok": -65,  "warn": -80},   # dBm (higher is better)
    },
    "NORMAL": {
        "latency":  {"ok": 50,   "warn": 150},
        "loss":     {"ok": 1,    "warn": 5},
        "jitter":   {"ok": 5,    "warn": 20},
        "dns":      {"ok": 50,   "warn": 200},
        "rssi":     {"ok": -60,  "warn": -75},
    },
    "STRICT": {
        "latency":  {"ok": 25,   "warn": 75},
        "loss":     {"ok": 0.5,  "warn": 2},
        "jitter":   {"ok": 2,    "warn": 10},
        "dns":      {"ok": 25,   "warn": 100},
        "rssi":     {"ok": -55,  "warn": -70},
    },
}


def classify(metric, value, profile_name="NORMAL"):
    """Return 'ok' | 'warn' | 'down' for a metric value against a profile."""
    if value is None:
        return "down"
    profile = PROFILES.get(profile_name, PROFILES["NORMAL"])
    bounds = profile.get(metric)
    if not bounds:
        return "ok"
    if metric == "rssi":
        # higher (less negative) is better
        if value >= bounds["ok"]:
            return "ok"
        if value >= bounds["warn"]:
            return "warn"
        return "down"
    if value <= bounds["ok"]:
        return "ok"
    if value <= bounds["warn"]:
        return "warn"
    return "down"


def channel_status(metrics_status):
    """Aggregate per-metric statuses into a channel-level status."""
    if "down" in metrics_status:
        return "down"
    if "warn" in metrics_status:
        return "warn"
    return "ok"
