"""WiFi Health — Tufty 2350 (badgeware-native, 3-screen).

Mirrors the Presto wifi_health app at apps/wifi_health/ — same CURRENT /
PING / CFG tabs and the same field labels (GATEWAY, INTERNET, RSSI,
RTT, LOSS, JIT, DNS) — but driven by buttons instead of touch:

  A = CURRENT  (and forces a fresh sample)
  B = PING     (RTT history per channel)
  C = CFG
  UP / DOWN    cycle the selected option on CFG
  HOME (BOOT)  returns to the launcher (hardware IRQ)

Real network probing: imports the badgeware `wifi` module to associate
with the AP listed in secrets.py (WIFI_SSID / WIFI_PASSWORD), then
times TCP connects to the gateway and a public host as a ping proxy.
"""

import os
import socket
import sys
import time

APP_DIR = "/system/apps/wifi_health_tufty"
try:
    sys.path.insert(0, APP_DIR)
    os.chdir(APP_DIR)
except (OSError, NameError):
    pass

import secrets

import network
import wifi  # noqa: F401 — badgeware's helper, drives the WLAN connect

# Avoid importing urequests at module top (heavy frozen module); we
# pull it in lazily inside the public-IP probe.
TARGET_SSID = getattr(secrets, "WIFI_SSID", "?")

# Tufty boots LORES (160x120) by default — switch to HIRES for 320x240.
badge.mode(HIRES | VSYNC)


# ── Theme ────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 320, 240
HEADER_H = 22
FOOTER_H = 22
BODY_TOP = HEADER_H
BODY_BOTTOM = HEIGHT - FOOTER_H
PADDING_X = 8
TAB_W = WIDTH // 3
VERSION = "v1.2"

BG = color.rgb(8, 20, 12)
FG = color.rgb(140, 235, 170)
DIM = color.rgb(60, 120, 90)
ACCENT = color.rgb(246, 200, 60)
BAD = color.rgb(230, 95, 70)
GOOD = color.rgb(110, 220, 120)

TABS = [("CURRENT", "current"), ("PING", "log"), ("CFG", "settings")]


def dashed_hline(y, x0=0, x1=WIDTH, on=4, off=6, pen=None):
    screen.pen = pen if pen is not None else DIM
    x = x0
    while x < x1:
        screen.shape(shape.rectangle(x, y, min(on, x1 - x), 1))
        x += on + off


# ── WiFi bring-up ────────────────────────────────────────────────────
# Kick off the association immediately; `wifi.tick()` in the update
# loop drives it through the various connection states.
try:
    wifi.connect()
except Exception:  # noqa: BLE001
    pass


# ── Network probes ───────────────────────────────────────────────────
def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _now_ms():
    return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)


def _tcp_ping(host, port=80, timeout=2):
    """Return RTT in ms for a TCP connect, or None on failure.

    MicroPython doesn't expose raw ICMP, so we approximate ping by
    timing a TCP three-way handshake to a well-known port. Loss /
    timeout shows up as None.
    """
    s = socket.socket()
    try:
        s.settimeout(timeout)
        t0 = _now_ms()
        info = socket.getaddrinfo(host, port)
        addr = info[0][-1]
        s.connect(addr)
        return _now_ms() - t0
    except (OSError, IndexError):
        return None
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


# ── Sampler ──────────────────────────────────────────────────────────
class Channel:
    """One ping target with rolling RTT history and derived stats."""

    HISTORY = 48

    def __init__(self, host_fn, port=80):
        self._host_fn = host_fn  # callable so we can resolve gateway lazily
        self.port = port
        self.rtts: list = []   # last N RTT samples in ms, or None for loss
        self.host = "—"

    def sample(self):
        host = self._host_fn()
        self.host = host if host else "—"
        if not host:
            self.rtts.append(None)
        else:
            self.rtts.append(_tcp_ping(host, self.port))
        if len(self.rtts) > self.HISTORY:
            self.rtts = self.rtts[-self.HISTORY:]

    @property
    def last(self):
        return self.rtts[-1] if self.rtts else None

    @property
    def loss_pct(self):
        if not self.rtts:
            return None
        bad = sum(1 for r in self.rtts if r is None)
        return 100.0 * bad / len(self.rtts)

    @property
    def avg_rtt(self):
        live = [r for r in self.rtts if r is not None]
        if not live:
            return None
        return sum(live) / len(live)

    @property
    def jitter_ms(self):
        live = [r for r in self.rtts if r is not None]
        if len(live) < 2:
            return None
        # Mean absolute difference of consecutive samples — what most
        # network gear calls "IPDV jitter".
        diffs = [abs(live[i] - live[i - 1]) for i in range(1, len(live))]
        return sum(diffs) / len(diffs)

    def status(self, ok_rtt=80, warn_rtt=200):
        if self.last is None:
            return "BAD"
        if (self.loss_pct or 0) > 20 or self.last > warn_rtt:
            return "BAD"
        if (self.loss_pct or 0) > 5 or self.last > ok_rtt:
            return "WARN"
        return "OK"


class Sampler:

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        _safe(lambda: self.wlan.active(True))
        # Gateway is whatever ifconfig reports as the default route.
        self.gateway = Channel(self._gateway_host, port=80)
        # Internet probe: Cloudflare DNS responds to TCP/53 reliably.
        self.internet = Channel(lambda: "1.1.1.1", port=53)
        self.connected = False
        self.ssid = "—"
        self.ip = "0.0.0.0"
        self.rssi = None
        self.public_ip = None
        self.last_sample_ms = -10_000
        self.last_public_ip_ms = -120_000  # force first fetch

    def _gateway_host(self):
        cfg = _safe(self.wlan.ifconfig, ("0.0.0.0", None, "", ""))
        if cfg and len(cfg) >= 3 and cfg[2]:
            return cfg[2]
        return None

    def _refresh_public_ip(self):
        """Best-effort fetch of our public IP via ipify; cached ~60s."""
        if not self.connected:
            return
        if (badge.ticks - self.last_public_ip_ms) < 60_000 and self.public_ip:
            return
        try:
            import urequests
            r = urequests.get("http://api.ipify.org", timeout=3)
            text = r.text.strip()
            r.close()
            # Sanity: must look like an IPv4 octet string.
            if text and text.count(".") == 3 and len(text) <= 15:
                self.public_ip = text
        except Exception:  # noqa: BLE001
            pass
        self.last_public_ip_ms = badge.ticks

    def sample(self):
        self.connected = _safe(self.wlan.isconnected, False) or False
        self.ssid = _safe(lambda: self.wlan.config("ssid"), self.ssid) or self.ssid
        cfg = _safe(self.wlan.ifconfig, ("0.0.0.0", None, "—", "—"))
        if cfg:
            self.ip = cfg[0]
        rssi = _safe(lambda: self.wlan.status("rssi"))
        if isinstance(rssi, (int, float)):
            self.rssi = int(rssi)
        if self.connected:
            self.gateway.sample()
            self.internet.sample()
            self._refresh_public_ip()
        else:
            # Record losses so the strip shows red while disconnected.
            self.gateway.rtts.append(None)
            self.internet.rtts.append(None)
            if len(self.gateway.rtts) > Channel.HISTORY:
                self.gateway.rtts = self.gateway.rtts[-Channel.HISTORY:]
            if len(self.internet.rtts) > Channel.HISTORY:
                self.internet.rtts = self.internet.rtts[-Channel.HISTORY:]
        self.last_sample_ms = badge.ticks

    def maybe_sample(self, force=False):
        if force or (badge.ticks - self.last_sample_ms) > 2000:
            self.sample()


# ── Settings ─────────────────────────────────────────────────────────
class Settings:
    FIELDS = [
        ("Sample period",   ["2s", "5s", "10s"]),
        ("RSSI bad <",      ["-85 dBm", "-80 dBm", "-75 dBm"]),
        ("Loss warn >",     ["1%", "5%", "10%"]),
        ("Theme",           ["Phosphor", "Amber", "Mono"]),
    ]

    def __init__(self):
        self.values = [0 for _ in self.FIELDS]
        self.selected = 0

    def move(self, delta):
        self.selected = (self.selected + delta) % len(self.FIELDS)

    def cycle(self, delta=1):
        choices = self.FIELDS[self.selected][1]
        self.values[self.selected] = (self.values[self.selected] + delta) % len(choices)

    def label(self, idx):
        return self.FIELDS[idx][0]

    def value(self, idx):
        return self.FIELDS[idx][1][self.values[idx]]


# ── Header / footer ──────────────────────────────────────────────────
def _status_color(s):
    if s == "OK":
        return GOOD
    if s == "WARN":
        return ACCENT
    return BAD


def draw_header(sampler, active_key):
    dashed_hline(HEADER_H - 1)
    screen.font = rom_font.sins
    label_for = {key: label for label, key in TABS}
    title = "> WIFI HEALTH . " + label_for.get(active_key, active_key).lower()
    screen.pen = FG
    screen.text(title, PADDING_X, 7)
    # Right-side: SSID + connection state
    if sampler.connected:
        right = "{}".format(sampler.ssid)
        rpen = GOOD
    else:
        right = "connecting…"
        rpen = ACCENT
    rw, _ = screen.measure_text(right)
    screen.pen = rpen
    screen.text(right, WIDTH - PADDING_X - rw, 7)


def draw_footer(active_key):
    y = BODY_BOTTOM
    dashed_hline(y)
    screen.font = rom_font.sins
    for i, (label, key) in enumerate(TABS):
        tx = i * TAB_W
        prefix = "[" + "ABC"[i] + "]"
        gap = 3
        pw, _ = screen.measure_text(prefix)
        lw, _ = screen.measure_text(label)
        total = pw + gap + lw
        x_text = tx + (TAB_W - total) // 2
        y_text = y + (FOOTER_H - 8) // 2
        screen.pen = FG
        screen.text(prefix, x_text, y_text)
        screen.pen = FG if key == active_key else DIM
        screen.text(label, x_text + pw + gap, y_text)


# ── Current screen ───────────────────────────────────────────────────
def _fmt_ms(v):
    if v is None:
        return "--"
    if v >= 100:
        return "{:d}".format(int(round(v)))
    return "{:.0f}".format(v)


def _fmt_loss(v):
    return "{:.0f}%".format(v) if v is not None else "--"


def _signal_bars(x, y, rssi):
    bars = 0 if rssi is None else max(0, min(5, (rssi + 95) // 8))
    for i in range(5):
        bx = x + i * 14
        bh = 5 + i * 4
        by = y - bh
        col = GOOD if rssi is not None and rssi >= -75 else (ACCENT if rssi is not None and rssi >= -85 else BAD)
        screen.pen = col if i < bars else DIM
        screen.shape(shape.rectangle(bx, by, 10, bh))


def _history_strip(x, y, w, h, rtts):
    """One vertical bar per sample, colored by per-sample status."""
    screen.pen = color.rgb(20, 50, 35)
    screen.shape(shape.rectangle(x, y, w, 1))
    screen.shape(shape.rectangle(x, y + h - 1, w, 1))
    if not rtts:
        return
    bw = max(1, w // len(rtts))
    for i, r in enumerate(rtts):
        if r is None:
            screen.pen = BAD
        elif r > 200:
            screen.pen = BAD
        elif r > 80:
            screen.pen = ACCENT
        else:
            screen.pen = GOOD
        screen.shape(shape.rectangle(x + i * bw, y + 1, bw - 1, h - 2))


def _draw_channel(y_top, name, channel):
    """One CURRENT row: GATEWAY or INTERNET. Header + metrics + strip."""
    dashed_hline(y_top, x0=PADDING_X, x1=WIDTH - PADDING_X)
    screen.font = rom_font.sins
    screen.pen = FG
    screen.text(name, PADDING_X, y_top + 6)
    # Host on the right
    screen.pen = DIM
    host_txt = str(channel.host)
    hw, _ = screen.measure_text(host_txt)
    screen.text(host_txt, WIDTH - PADDING_X - hw, y_top + 6)
    # Status pill below the host
    status = channel.status()
    spen = _status_color(status)
    screen.pen = spen
    sw, _ = screen.measure_text(status)
    screen.text(status, WIDTH - PADDING_X - sw, y_top + 20)

    metrics = [
        ("RTT",  _fmt_ms(channel.last)),
        ("LOSS", _fmt_loss(channel.loss_pct)),
        ("JIT",  _fmt_ms(channel.jitter_ms)),
        ("AVG",  _fmt_ms(channel.avg_rtt)),
    ]
    mx = PADDING_X
    for label, val in metrics:
        screen.pen = DIM
        screen.text(label, mx, y_top + 22)
        screen.pen = FG
        screen.text(val, mx + 26, y_top + 22)
        mx += 70

    _history_strip(PADDING_X, y_top + 38, WIDTH - 2 * PADDING_X, 10, channel.rtts)


def draw_current(sampler):
    # Compact channel blocks so we have room for an IP info row.
    block_h = 56
    gw_y = BODY_TOP + 6
    net_y = gw_y + block_h + 8
    _draw_channel(gw_y, "GATEWAY",  sampler.gateway)
    _draw_channel(net_y, "INTERNET", sampler.internet)

    # IP info row — local / gateway / public
    info_y = net_y + block_h + 4
    screen.font = rom_font.sins
    cells = [
        ("LOCAL",   sampler.ip if sampler.connected else "—"),
        ("GATEWAY", sampler.gateway.host if sampler.gateway.host else "—"),
        ("PUBLIC",  sampler.public_ip if sampler.public_ip else "…"),
    ]
    cell_w = (WIDTH - 2 * PADDING_X) // 3
    for i, (label, val) in enumerate(cells):
        cx = PADDING_X + i * cell_w
        screen.pen = DIM
        screen.text(label, cx, info_y)
        screen.pen = FG
        screen.text(str(val), cx, info_y + 9)

    # Signal strip
    screen.pen = DIM
    screen.text("RSSI", PADDING_X, BODY_BOTTOM - 18)
    screen.pen = FG
    rssi_txt = "{} dBm".format(sampler.rssi) if sampler.rssi is not None else "-- dBm"
    screen.text(rssi_txt, PADDING_X + 32, BODY_BOTTOM - 18)
    _signal_bars(WIDTH - 80, BODY_BOTTOM - 6, sampler.rssi)


# ── Connecting splash ────────────────────────────────────────────────
def draw_connecting():
    """Full-screen loader shown until wifi.connect() succeeds.

    Title + status text + an indeterminate progress bar that sweeps
    left-right while we wait for the WLAN association.
    """
    screen.pen = BG
    screen.clear()

    screen.font = rom_font.ark
    screen.pen = FG
    title = "> WIFI HEALTH"
    tw, _ = screen.measure_text(title)
    screen.text(title, (WIDTH - tw) // 2, 38)

    screen.font = rom_font.sins
    screen.pen = ACCENT
    line1 = "Connecting to"
    w1, _ = screen.measure_text(line1)
    screen.text(line1, (WIDTH - w1) // 2, 88)
    screen.pen = FG
    line2 = TARGET_SSID
    w2, _ = screen.measure_text(line2)
    screen.text(line2, (WIDTH - w2) // 2, 102)

    # Indeterminate sweep bar
    bar_x, bar_y, bar_w, bar_h = 30, 140, WIDTH - 60, 12
    screen.pen = DIM
    screen.shape(shape.rectangle(bar_x, bar_y, bar_w, bar_h))
    sweep_w = 60
    cycle = max(1, bar_w - sweep_w)
    pos = (badge.ticks // 12) % (2 * cycle)
    if pos > cycle:
        pos = 2 * cycle - pos
    screen.pen = FG
    screen.shape(shape.rectangle(bar_x + pos, bar_y + 2, sweep_w, bar_h - 4))

    screen.pen = DIM
    hint = "HOME (back) to cancel"
    hw, _ = screen.measure_text(hint)
    screen.text(hint, (WIDTH - hw) // 2, 200)


# ── Ping history screen ──────────────────────────────────────────────
def _draw_ping_panel(x, y, w, h, name, channel):
    """Big RTT trend plot for one channel, with the latest reading."""
    screen.font = rom_font.sins
    screen.pen = FG
    screen.text(name, x, y)
    screen.pen = _status_color(channel.status())
    last_txt = "{} ms".format(int(round(channel.last))) if channel.last is not None else "loss"
    lw, _ = screen.measure_text(last_txt)
    screen.text(last_txt, x + w - lw, y)

    plot_y = y + 12
    plot_h = h - 14

    # Grid
    screen.pen = color.rgb(20, 50, 35)
    for ty in range(plot_y, plot_y + plot_h, 8):
        screen.shape(shape.rectangle(x, ty, w, 1))

    if not channel.rtts:
        screen.pen = DIM
        screen.text("(no samples)", x + 4, plot_y + plot_h // 2 - 4)
        return

    # Scale: 0..500ms maps to plot_h. Cap visually.
    live = [r for r in channel.rtts if r is not None]
    if live:
        max_rtt = max(500, max(live) * 1.2)
    else:
        max_rtt = 500
    bw = max(1, w // len(channel.rtts))
    for i, r in enumerate(channel.rtts):
        bx = x + i * bw
        if r is None:
            screen.pen = BAD
            screen.shape(shape.rectangle(bx, plot_y, bw - 1, plot_h))
            continue
        bh = max(1, int(plot_h * min(1.0, r / max_rtt)))
        if r > 200:
            screen.pen = BAD
        elif r > 80:
            screen.pen = ACCENT
        else:
            screen.pen = GOOD
        screen.shape(shape.rectangle(bx, plot_y + plot_h - bh, bw - 1, bh))


def draw_ping(sampler):
    panel_h = (BODY_BOTTOM - BODY_TOP) // 2 - 6
    _draw_ping_panel(PADDING_X, BODY_TOP + 8, WIDTH - 2 * PADDING_X, panel_h,
                     "GATEWAY  " + str(sampler.gateway.host), sampler.gateway)
    _draw_ping_panel(PADDING_X, BODY_TOP + panel_h + 14, WIDTH - 2 * PADDING_X, panel_h,
                     "INTERNET  " + str(sampler.internet.host), sampler.internet)


# ── Settings screen ──────────────────────────────────────────────────
def draw_settings(settings_state):
    screen.font = rom_font.sins
    y = BODY_TOP + 8
    for i in range(len(settings_state.FIELDS)):
        is_sel = (i == settings_state.selected)
        screen.pen = ACCENT if is_sel else DIM
        screen.text(">" if is_sel else " ", PADDING_X, y)
        screen.pen = FG
        screen.text(settings_state.label(i), PADDING_X + 14, y)
        val = settings_state.value(i)
        vw, _ = screen.measure_text(val)
        screen.pen = ACCENT if is_sel else FG
        screen.text(val, WIDTH - PADDING_X - vw, y)
        y += 22

    screen.pen = DIM
    screen.text("UP/DOWN: select   A: cycle   HOME: quit",
                PADDING_X, BODY_BOTTOM - 18)


# ── Input + main loop ────────────────────────────────────────────────
BUTTONS = (
    ("A", BUTTON_A),
    ("B", BUTTON_B),
    ("C", BUTTON_C),
    ("UP", BUTTON_UP),
    ("DOWN", BUTTON_DOWN),
)


sampler = Sampler()
settings_state = Settings()

active = "current"
button_prev = {name: False for name, _ in BUTTONS}


def update():
    global active

    # Keep driving the WiFi association until connected. While we wait,
    # take over the screen with the connecting splash — there's nothing
    # useful to show on the normal screens until we have a link.
    if not sampler.connected:
        try:
            wifi.tick()
        except Exception:  # noqa: BLE001
            pass
        # Also refresh sampler state so .connected flips as soon as
        # the underlying WLAN reports up.
        sampler.connected = _safe(sampler.wlan.isconnected, False) or False
        if not sampler.connected:
            draw_connecting()
            return None

    for name, btn in BUTTONS:
        is_down = badge.held(btn)
        fired = is_down and not button_prev[name]
        button_prev[name] = is_down
        if not fired:
            continue
        if name == "A":
            if active == "settings":
                settings_state.cycle(1)
            else:
                active = "current"
                sampler.maybe_sample(force=True)
        elif name == "B":
            active = "log"
        elif name == "C":
            active = "settings"
        elif name == "UP" and active == "settings":
            settings_state.move(-1)
        elif name == "DOWN" and active == "settings":
            settings_state.move(1)

    sampler.maybe_sample()

    screen.pen = BG
    screen.clear()
    draw_header(sampler, active)
    if active == "current":
        draw_current(sampler)
    elif active == "log":
        draw_ping(sampler)
    else:
        draw_settings(settings_state)
    draw_footer(active)
    return None


run(update)
