"""Birthday countdown with rainbow animations for Presto.

Counts down to a target time with rainbow arcs, bubbles, confetti,
twinkling stars, LED chase effects, and a celebration mode at zero.

Configuration: edit the block below.
"""

import math
import time

from presto import Buzzer, Presto

# ─── Configuration ───────────────────────────────────────────────
PERSON_NAME = "Lise"           # Name shown on boot screen and main message
TARGET_HOUR = 15               # Countdown target hour (local time)
TARGET_MINUTE = 0              # Countdown target minute
START_HOUR = 8                 # Progress bar fills from this hour
WIFI_SSID = "tartiflon"        # WiFi network name (set to "" to skip WiFi)
WIFI_PASSWORD = "tartiflette"  # WiFi password
# ─────────────────────────────────────────────────────────────────

TOTAL_SECONDS = (TARGET_HOUR - START_HOUR) * 3600 + TARGET_MINUTE * 60

# ─── Init Presto ─────────────────────────────────────────────────
presto = Presto()
display = presto.display
WIDTH, HEIGHT = display.get_bounds()  # 240x240 (hardware upscales to 480)
buzzer = Buzzer(43)

# ─── Boot animation helpers ──────────────────────────────────────
_BOOT_BG = display.create_pen(20, 10, 35)
_BOOT_WHITE = display.create_pen(255, 255, 255)
_BOOT_GREEN = display.create_pen(80, 255, 80)
_BOOT_RED = display.create_pen(255, 80, 80)
_BOOT_DIM = display.create_pen(60, 40, 80)

_boot_step = 0


def _boot_screen(status_text, step, color=None):
    """Draw boot screen with rainbow loading bar and status."""
    global _boot_step
    _boot_step = step
    cx = WIDTH // 2

    display.set_pen(_BOOT_BG)
    display.clear()

    # Title
    tw = display.measure_text(PERSON_NAME, scale=3, spacing=1)
    display.set_pen(_BOOT_WHITE)
    display.text(PERSON_NAME, cx - tw // 2, 30, -1, scale=3, spacing=1)

    # Small rainbow arc (decorative)
    for i in range(7):
        r = 50 - i * 5
        pen = display.create_pen_hsv(i / 7.0, 0.9, 0.85)
        display.set_pen(pen)
        for dy in range(-r, -r + 5):
            dx2 = r * r - dy * dy
            if dx2 > 0:
                dx = int(math.sqrt(dx2))
                display.rectangle(cx - dx, 75 + dy + r, dx * 2, 1)

    # Loading bar background (3 steps: WiFi, NTP, Done)
    bar_w = 160
    bar_h = 8
    bx = cx - bar_w // 2
    by = 130
    display.set_pen(_BOOT_DIM)
    display.rectangle(bx, by, bar_w, bar_h)

    fill = int(bar_w * step / 3)
    if fill > 0:
        for x in range(0, fill, 4):
            w = min(4, fill - x)
            pen = display.create_pen_hsv(x / bar_w, 0.9, 1.0)
            display.set_pen(pen)
            display.rectangle(bx + x, by + 1, w, bar_h - 2)

    # Status text
    c = color if color else _BOOT_WHITE
    display.set_pen(c)
    sw = display.measure_text(status_text, scale=2, spacing=1)
    display.text(status_text, cx - sw // 2, 150, -1, scale=2, spacing=1)

    presto.update()


# ─── Time sync: try NTP, fallback to RTC ────────────────────────

def _utc_to_local(utc):
    month, day = utc[1], utc[2]
    if 4 <= month <= 9:
        offset = 2
    elif month == 3 and day >= 25:
        offset = 2
    elif month == 10 and day < 25:
        offset = 2
    else:
        offset = 1
    local_secs = time.mktime(utc) + offset * 3600
    return time.localtime(local_secs)


def _time_is_sane():
    return time.localtime()[0] >= 2025


import machine
rtc = machine.RTC()
time_source = None

if _time_is_sane():
    time_source = "RTC"

_boot_screen("WiFi...", 0)

if WIFI_SSID:
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _i in range(100):
            if wlan.isconnected():
                break
            if _i % 10 == 0:
                dots = "." * ((_i // 10) % 4)
                _boot_screen("WiFi" + dots, 0)
            time.sleep(0.1)

        if wlan.isconnected():
            _boot_screen("WiFi OK !", 1, _BOOT_GREEN)
            time.sleep(0.3)

            _boot_screen("Sync NTP...", 1)
            import ntptime
            for _attempt in range(3):
                try:
                    ntptime.settime()
                    utc = time.localtime()
                    if utc[0] >= 2025:
                        local = _utc_to_local(utc)
                        rtc.datetime((local[0], local[1], local[2], local[6], local[3], local[4], local[5], 0))
                        time_source = "NTP"
                        break
                except Exception:
                    pass
                _boot_screen("NTP retry...", 1)
                time.sleep(1)

            if time_source == "NTP":
                _boot_screen("NTP OK !", 2, _BOOT_GREEN)
            else:
                _boot_screen("NTP failed", 2, _BOOT_RED)
        else:
            _boot_screen("WiFi failed", 1, _BOOT_RED)
    except Exception:
        _boot_screen("Network error", 1, _BOOT_RED)
else:
    _boot_screen("No WiFi", 1, _BOOT_DIM)

time.sleep(0.3)
if time_source:
    now = time.localtime()
    _boot_screen("{:02d}:{:02d} - Ready!".format(now[3], now[4]), 3, _BOOT_GREEN)
else:
    _boot_screen("No time source!", 3, _BOOT_RED)
time.sleep(1)

# ─── Simple PRNG (no import random on MicroPython) ──────────────
_seed = 54321


def rng():
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed


def rng_range(a, b):
    return a + rng() % (b - a + 1)


def rng_float():
    return (rng() & 0xFFFF) / 65536.0


# ─── HSV helper with bounded cache ──────────────────────────────
_pen_cache = {}
_PEN_CACHE_MAX = 512


def hsv_pen(h, s, v):
    key = (int(h * 200), int(s * 20), int(v * 20))
    pen = _pen_cache.get(key)
    if pen is None:
        if len(_pen_cache) >= _PEN_CACHE_MAX:
            _pen_cache.clear()
        pen = display.create_pen_hsv(h % 1.0, s, v)
        _pen_cache[key] = pen
    return pen


# ─── Rainbow palette (7 bands) ──────────────────────────────────
RAINBOW_HUES = [0.0, 0.05, 0.1, 0.15, 0.33, 0.55, 0.75]  # R O Y G B I V

# ─── Pre-create common pens ─────────────────────────────────────
BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)
DARK_BG = display.create_pen(20, 10, 35)
BAR_BG = display.create_pen(40, 20, 60)


# ─── Particle classes ───────────────────────────────────────────
class Bubble:
    __slots__ = ("x", "y", "old_x", "old_y", "r", "hue", "speed", "wobble_phase", "wobble_amp")

    def __init__(self):
        self.old_x = -100
        self.old_y = -100
        self.respawn()

    def respawn(self):
        self.x = rng_range(15, WIDTH - 15)
        self.y = HEIGHT + rng_range(5, 30)
        self.old_x = self.x
        self.old_y = self.y
        self.r = rng_range(3, 7)
        self.hue = rng_float()
        self.speed = 1.0 + rng_float() * 2.0
        self.wobble_phase = rng_float() * 6.28
        self.wobble_amp = rng_range(8, 20)

    def update(self, t):
        self.old_x = self.x
        self.old_y = self.y
        self.y -= self.speed
        self.x += math.sin(self.wobble_phase + t * 2.0) * 0.6
        if self.y < -self.r * 2:
            self.respawn()

    def erase(self):
        display.set_pen(DARK_BG)
        r = self.r + 2
        display.rectangle(int(self.old_x) - r, int(self.old_y) - r, r * 2 + 1, r * 2 + 1)

    def draw(self, t):
        hue = (self.hue + t * 0.05) % 1.0
        pen = hsv_pen(hue, 0.6, 0.9)
        display.set_pen(pen)
        display.circle(int(self.x), int(self.y), self.r)
        display.set_pen(WHITE)
        display.rectangle(int(self.x) - self.r // 3, int(self.y) - self.r // 3, 2, 2)


class Confetti:
    __slots__ = ("x", "y", "vx", "vy", "hue", "size", "life")

    def __init__(self):
        self.life = 0

    def spawn(self, x, y):
        angle = rng_float() * 6.28
        speed = 1.0 + rng_float() * 3.0
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 3.0
        self.hue = rng_float()
        self.size = rng_range(2, 4)
        self.life = rng_range(30, 70)

    def update(self):
        if self.life <= 0:
            return
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.vx *= 0.98
        self.life -= 1
        if self.x < 0 or self.x > WIDTH or self.y > HEIGHT + 20:
            self.life = 0

    def draw(self, t):
        if self.life <= 0:
            return
        hue = (self.hue + t * 0.1) % 1.0
        alpha = min(1.0, self.life / 15.0)
        pen = hsv_pen(hue, 0.9, alpha)
        display.set_pen(pen)
        display.rectangle(int(self.x), int(self.y), self.size, self.size)


class CelebrationConfetti:
    """Confetti falling from the top for celebration mode."""
    __slots__ = ("x", "y", "vy", "vx", "hue", "size", "wobble")

    def __init__(self):
        self.respawn()

    def respawn(self):
        self.x = float(rng_range(0, WIDTH))
        self.y = float(rng_range(-30, -3))
        self.vy = 0.8 + rng_float() * 1.5
        self.vx = (rng_float() - 0.5) * 0.8
        self.hue = rng_float()
        self.size = rng_range(2, 4)
        self.wobble = rng_float() * 6.28

    def update(self, t):
        self.y += self.vy
        self.x += self.vx + math.sin(self.wobble + t * 3.0) * 0.8
        if self.y > HEIGHT + 20:
            self.respawn()

    def draw(self, t):
        hue = (self.hue + t * 0.05) % 1.0
        pen = hsv_pen(hue, 1.0, 1.0)
        display.set_pen(pen)
        display.rectangle(int(self.x), int(self.y), self.size, self.size // 2 + 1)


class Star:
    __slots__ = ("x", "y", "hue", "phase", "speed")

    def __init__(self):
        self.x = rng_range(5, WIDTH - 5)
        self.y = rng_range(5, HEIGHT - 5)
        self.hue = rng_float()
        self.phase = rng_float() * 6.28
        self.speed = 1.5 + rng_float() * 3.0

    def draw(self, t):
        brightness = (math.sin(self.phase + t * self.speed) + 1.0) * 0.5
        if brightness < 0.3:
            return
        pen = hsv_pen(self.hue + t * 0.02, 0.5, brightness)
        display.set_pen(pen)
        s = 2 if brightness > 0.7 else 1
        display.rectangle(self.x - s, self.y, s * 2 + 1, 1)
        display.rectangle(self.x, self.y - s, 1, s * 2 + 1)


class CelebrationStar:
    """Spinning triangle star for celebration mode."""
    __slots__ = ("x", "y", "vy", "hue", "angle", "spin", "size")

    def __init__(self):
        self.respawn()

    def respawn(self):
        self.x = rng_range(10, WIDTH - 10)
        self.y = float(rng_range(-20, -3))
        self.vy = 0.5 + rng_float() * 1.2
        self.hue = rng_float()
        self.angle = rng_float() * 6.28
        self.spin = (rng_float() - 0.5) * 0.2
        self.size = rng_range(3, 7)

    def update(self, t):
        self.y += self.vy
        self.angle += self.spin
        if self.y > HEIGHT + 20:
            self.respawn()

    def draw(self, t):
        pen = hsv_pen((self.hue + t * 0.08) % 1.0, 1.0, 1.0)
        display.set_pen(pen)
        cx, cy = int(self.x), int(self.y)
        s = self.size
        a = self.angle
        x1 = cx + int(math.cos(a) * s)
        y1 = cy + int(math.sin(a) * s)
        x2 = cx + int(math.cos(a + 2.094) * s)
        y2 = cy + int(math.sin(a + 2.094) * s)
        x3 = cx + int(math.cos(a + 4.189) * s)
        y3 = cy + int(math.sin(a + 4.189) * s)
        display.triangle(x1, y1, x2, y2, x3, y3)


# ─── Create particles ───────────────────────────────────────────
bubbles = [Bubble() for _ in range(8)]
stars = [Star() for _ in range(10)]
confettis = [Confetti() for _ in range(50)]
celeb_confettis = [CelebrationConfetti() for _ in range(30)]
celeb_stars = [CelebrationStar() for _ in range(12)]

# ─── State ───────────────────────────────────────────────────────
celebrating = False
celeb_start_time = 0
melody_played = False
frame = 0
last_second = -1


# ─── Drawing helpers ─────────────────────────────────────────────
def draw_bg(t):
    display.set_pen(DARK_BG)
    display.clear()


# Pre-compute arc geometry and pens once (static rainbow)
_ARC_CX = WIDTH // 2
_ARC_CY = 85
_ARC_BASE_R = 90
_ARC_BAND_W = 7
_ARC_PENS = [hsv_pen(RAINBOW_HUES[i], 0.9, 0.85) for i in range(7)]
_ARC_SPANS = []  # list of (y, x_left, x_right, width, pen)
for _y in range(0, _ARC_CY + 1, 2):
    _dy = _y - _ARC_CY
    _dy2 = _dy * _dy
    for _i in range(7):
        _outer = _ARC_BASE_R - _i * _ARC_BAND_W
        _inner = _outer - _ARC_BAND_W
        if _dy2 > _outer * _outer:
            continue
        _ox = int(math.sqrt(_outer * _outer - _dy2))
        if _inner > 0 and _dy2 < _inner * _inner:
            _ix = int(math.sqrt(_inner * _inner - _dy2))
        else:
            _ix = 0
        _w = _ox - _ix
        if _w > 0:
            _ARC_SPANS.append((_y, _ARC_CX - _ox, _ARC_CX + _ix, _w, _ARC_PENS[_i]))


def draw_rainbow_arc():
    for y, xl, xr, w, pen in _ARC_SPANS:
        display.set_pen(pen)
        display.rectangle(xl, y, w, 2)
        display.rectangle(xr, y, w, 2)


def draw_countdown(seconds_left, t):
    h = seconds_left // 3600
    m = (seconds_left % 3600) // 60
    s = seconds_left % 60
    text = "{:02d}:{:02d}:{:02d}".format(h, m, s)

    cx = WIDTH // 2
    cy = HEIGHT // 2 - 5
    text_w = display.measure_text(text, scale=3, spacing=1)
    tx = cx - text_w // 2
    ty = cy - 10

    # Rainbow shadow
    hue = (t * 0.1) % 1.0
    pen = hsv_pen(hue, 1.0, 0.7)
    display.set_pen(pen)
    display.text(text, tx + 2, ty + 2, -1, scale=3, spacing=1)

    display.set_pen(WHITE)
    display.text(text, tx, ty, -1, scale=3, spacing=1)


def draw_message(seconds_left, t):
    if seconds_left < 60:
        msg = "PRESQUE !"
    else:
        msg = "Anniversaire de " + PERSON_NAME

    msg_w = display.measure_text(msg, scale=2, spacing=1)
    mx = WIDTH // 2 - msg_w // 2
    my = HEIGHT // 2 + 25

    hue = (t * 0.15) % 1.0
    pen = hsv_pen(hue, 0.8, 1.0)
    display.set_pen(pen)
    display.text(msg, mx, my, -1, scale=2, spacing=1)


def draw_progress_bar(seconds_left, total_seconds, t):
    bar_w = 170
    bar_h = 10
    bx = WIDTH // 2 - bar_w // 2
    by = HEIGHT // 2 + 45

    display.set_pen(BAR_BG)
    display.rectangle(bx, by, bar_w, bar_h)

    progress = 1.0 - (seconds_left / max(1, total_seconds))
    fill_w = int(bar_w * max(0.0, min(1.0, progress)))

    if fill_w > 0:
        step = 4
        for x in range(0, fill_w, step):
            w = min(step, fill_w - x)
            hue = (x / bar_w + t * 0.1) % 1.0
            pen = hsv_pen(hue, 0.9, 1.0)
            display.set_pen(pen)
            display.rectangle(bx + x, by + 2, w, bar_h - 4)

    if fill_w > 4:
        sparkle = 0.5 + math.sin(t * 6.0) * 0.5
        pen = hsv_pen((t * 0.3) % 1.0, 0.3, sparkle)
        display.set_pen(pen)
        display.rectangle(bx + fill_w - 2, by, 4, bar_h)


def draw_celebration_bg(t):
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_r = 200
    num_rings = 8
    speed = t * 30.0

    for i in range(num_rings):
        r = int((speed + i * (max_r / num_rings)) % max_r)
        if r < 5:
            continue
        hue = (i / num_rings + t * 0.1) % 1.0
        pen = hsv_pen(hue, 1.0, 0.8)
        display.set_pen(pen)
        display.circle(cx, cy, r)
        if r > 15:
            inner_hue = ((i + 1) / num_rings + t * 0.1) % 1.0
            inner_pen = hsv_pen(inner_hue, 1.0, 0.5)
            display.set_pen(inner_pen)
            display.circle(cx, cy, r - 6)


def draw_celebration_text(t):
    msg = "JOYEUX"
    msg2 = "ANNIVERSAIRE !"

    bounce_y = int(math.sin(t * 3.0) * 10)

    w1 = display.measure_text(msg, scale=3, spacing=1)
    x1 = WIDTH // 2 - w1 // 2
    y1 = HEIGHT // 2 - 30 + bounce_y
    hue = (t * 0.2) % 1.0
    pen = hsv_pen(hue, 1.0, 1.0)
    display.set_pen(pen)
    display.text(msg, x1, y1, -1, scale=3, spacing=1)

    w2 = display.measure_text(msg2, scale=2, spacing=1)
    x2 = WIDTH // 2 - w2 // 2
    y2 = HEIGHT // 2 + 5 + bounce_y
    hue2 = (hue + 0.3) % 1.0
    pen2 = hsv_pen(hue2, 1.0, 1.0)
    display.set_pen(pen2)
    display.text(msg2, x2, y2, -1, scale=2, spacing=1)


# ─── Birthday melody (Joyeux Anniversaire) ───────────────────────
MELODY = [
    (262, 0.25), (262, 0.25), (294, 0.5), (262, 0.5), (349, 0.5), (330, 0.7),
    (262, 0.25), (262, 0.25), (294, 0.5), (262, 0.5), (392, 0.5), (349, 0.7),
    (262, 0.25), (262, 0.25), (523, 0.5), (440, 0.5), (349, 0.5), (330, 0.5), (294, 0.7),
    (466, 0.25), (466, 0.25), (440, 0.5), (349, 0.5), (392, 0.5), (349, 0.9),
]


def play_melody():
    for freq, dur in MELODY:
        buzzer.set_tone(freq, 0.5)
        time.sleep(dur)
    buzzer.stop()


# ─── LED effects ─────────────────────────────────────────────────
def update_leds_chase(t):
    for i in range(7):
        hue = (i / 7.0 + t * 0.3) % 1.0
        presto.set_led_hsv(i, hue, 1.0, 0.5)


def update_leds_flash(t):
    for i in range(7):
        hue = (i / 7.0 + t * 1.5) % 1.0
        v = 0.5 + math.sin(t * 8.0 + i) * 0.5
        presto.set_led_hsv(i, hue, 1.0, max(0.0, v))


# ─── Compute remaining seconds ──────────────────────────────────
def get_seconds_left():
    now = time.localtime()
    target_secs = TARGET_HOUR * 3600 + TARGET_MINUTE * 60
    now_secs = now[3] * 3600 + now[4] * 60 + now[5]
    remaining = target_secs - now_secs
    if remaining < 0:
        remaining = 0
    return remaining


# ─── Main loop ───────────────────────────────────────────────────
TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS
presto.set_backlight(1.0)
t0 = time.ticks_ms() if hasattr(time, 'ticks_ms') else int(time.time() * 1000)

while True:
    frame_start = time.ticks_ms() if hasattr(time, 'ticks_ms') else int(time.time() * 1000)
    t = (frame_start - t0) / 1000.0
    seconds_left = get_seconds_left()

    # Touch: spawn confetti burst
    touch = presto.touch_a
    if touch.touched:
        tx, ty = touch.x, touch.y
        count = 0
        for c in confettis:
            if count >= 12:
                break
            if c.life <= 0:
                c.spawn(tx, ty)
                count += 1

    # Celebration transition
    if seconds_left <= 0 and not celebrating:
        celebrating = True
        celeb_start_time = t
        play_melody()
        melody_played = True

    display.set_layer(0)

    if not celebrating:
        # ════════ COUNTDOWN MODE ════════════════════════════
        draw_bg(t)
        draw_rainbow_arc()
        for b in bubbles:
            b.update(t)
            b.draw(t)
        for s in stars:
            s.draw(t)
        draw_countdown(seconds_left, t)
        draw_message(seconds_left, t)
        draw_progress_bar(seconds_left, TOTAL_SECONDS, t)
        for c in confettis:
            c.update()
            c.draw(t)
        update_leds_chase(t)
    else:
        # ════════ CELEBRATION MODE ══════════════════════════
        draw_celebration_bg(t)
        for c in celeb_confettis:
            c.update(t)
            c.draw(t)
        for s in celeb_stars:
            s.update(t)
            s.draw(t)
        for c in confettis:
            c.update()
            c.draw(t)
        draw_celebration_text(t)

        celeb_elapsed = t - celeb_start_time
        if celeb_elapsed > 5.0 and int(celeb_elapsed) % 8 == 0 and frame % 20 == 0:
            buzzer.play_tone(523, 0.08)

        update_leds_flash(t)

    presto.update()
    frame += 1

    # FPS limiter
    frame_end = time.ticks_ms() if hasattr(time, 'ticks_ms') else int(time.time() * 1000)
    elapsed_ms = frame_end - frame_start
    sleep_ms = int(FRAME_TIME * 1000) - elapsed_ms
    if sleep_ms > 0:
        time.sleep(sleep_ms / 1000.0)
