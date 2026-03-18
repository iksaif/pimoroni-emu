"""All drawing functions for the On This Day display."""

import math
from config import DARK_THEME, s, month_name, years_ago_str


# ─── Layout profile: all size-dependent values in one place ──────
class Layout:
    """Screen layout computed from display dimensions."""

    # Size profiles: S=Badger, M=Tufty, L=Presto/Inky
    _PROFILES = {
        "S": dict(margin=6, header_h=20, timescale_h=14, icon_size=0,
                  scale_title=2, scale_year=2, scale_name=0, scale_body=2,
                  scale_body_small=1, scale_ago=1, scale_boot_title=2, scale_boot_msg=1),
        "M": dict(margin=10, header_h=28, timescale_h=18, icon_size=0,
                  scale_title=2, scale_year=2, scale_name=0, scale_body=2,
                  scale_body_small=1, scale_ago=1, scale_boot_title=2, scale_boot_msg=2),
        "L": dict(margin=20, header_h=60, timescale_h=24, icon_size=72,
                  scale_title=4, scale_year=4, scale_name=2, scale_body=3,
                  scale_body_small=2, scale_ago=2, scale_boot_title=4, scale_boot_msg=3),
    }

    # Approximate line height per bitmap scale factor
    LINE_HEIGHT = {1: 12, 2: 20, 3: 30, 4: 40}

    def __init__(self, width, height):
        dim = min(width, height)
        size = "S" if dim < 200 else ("M" if dim < 400 else "L")
        for key, val in self._PROFILES[size].items():
            setattr(self, key, val)

    def line_height(self, scale):
        return self.LINE_HEIGHT.get(scale, scale * 10)


# ─── Event helper ────────────────────────────────────────────────
class Event:
    """Wraps a raw event tuple for readable access."""
    __slots__ = ("year", "text", "icons", "title", "is_birth")

    def __init__(self, raw):
        self.year = raw[0]
        self.text = raw[1]
        self.icons = raw[2] if len(raw) > 2 else []
        self.title = raw[3] if len(raw) > 3 else ""
        self.is_birth = raw[4] if len(raw) > 4 else False


# ─── Module state ────────────────────────────────────────────────
display = presto = None
WIDTH = HEIGHT = 0
IS_EINK = HAS_TOUCH = False
layout = None  # type: Layout
today_year = today_month = today_day = 0

# Pens (initialized by init)
BG = TEXT = DIM = HEADER_BG = TIMESCALE_BG = 0
ERR_PEN = OK_PEN = WHITE = BIRTH_PEN = 0
_fade_bgs = []
_pen_cache = {}

TIMESCALE_START_YEAR = -1000  # 1000 BC


def _hsv_pen(hue, saturation, value):
    """Create/cache an HSV pen."""
    key = (int(hue * 200), int(saturation * 20), int(value * 20))
    pen = _pen_cache.get(key)
    if pen is None:
        if len(_pen_cache) >= 256:
            _pen_cache.clear()
        pen = display.create_pen_hsv(hue % 1.0, saturation, value)
        _pen_cache[key] = pen
    return pen


def init(disp, prest, w, h, year, month, day):
    """Initialize drawing module. Call once after display is ready."""
    global display, presto, WIDTH, HEIGHT, IS_EINK, HAS_TOUCH, layout
    global BG, TEXT, DIM, HEADER_BG, TIMESCALE_BG
    global ERR_PEN, OK_PEN, WHITE, BIRTH_PEN
    global today_year, today_month, today_day

    display, presto = disp, prest
    WIDTH, HEIGHT = w, h
    today_year, today_month, today_day = year, month, day
    HAS_TOUCH = presto is not None
    IS_EINK = w > 400 and h > 200 and presto is None
    layout = Layout(w, h)

    if DARK_THEME and not IS_EINK:
        BG = display.create_pen(15, 12, 30)
        TEXT = display.create_pen(230, 230, 230)
        DIM = display.create_pen(60, 50, 80)
        HEADER_BG = display.create_pen(25, 20, 50)
        TIMESCALE_BG = display.create_pen(30, 25, 55)
    else:
        BG = display.create_pen(255, 255, 255)
        TEXT = display.create_pen(0, 0, 0)
        DIM = display.create_pen(160, 160, 160)
        HEADER_BG = display.create_pen(235, 235, 240)
        TIMESCALE_BG = display.create_pen(220, 220, 230)
    ERR_PEN = display.create_pen(255, 80, 80)
    OK_PEN = display.create_pen(80, 255, 80)
    WHITE = display.create_pen(255, 255, 255)
    BIRTH_PEN = display.create_pen(255, 180, 100)

    _fade_bgs.clear()
    if not IS_EINK:
        for i in range(11):
            f = i / 10.0
            _fade_bgs.append(display.create_pen(int(15 * f), int(12 * f), int(30 * f)))


def _flush():
    """Push framebuffer to screen."""
    if presto:
        presto.update()
    else:
        display.update()


def _word_wrap(text, max_width, scale):
    """Break text into lines that fit within max_width at given scale."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = current + (" " if current else "") + word
        if display.measure_text(candidate, scale=scale, spacing=1) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ─── Boot screen ─────────────────────────────────────────────────

def boot_screen(message, step, color=None):
    """Draw a boot progress screen."""
    total_steps = 5
    cx = WIDTH // 2
    lo = layout

    if presto:
        display.set_layer(0)
    display.set_pen(BG)
    display.clear()

    # Title
    scale = lo.scale_boot_title
    title = s("title")
    tw = display.measure_text(title, scale=scale, spacing=1)
    display.set_pen(TEXT)
    display.text(title, cx - tw // 2, HEIGHT // 4 - 4 * scale, -1, scale=scale, spacing=1)

    # Rainbow dots (large screens only)
    if lo.scale_name:
        dot_y = HEIGHT // 4 + 5 * scale + 5
        for i in range(5):
            display.set_pen(_hsv_pen(i / 5.0, 0.8, 0.85))
            display.circle(cx + (i - 2) * 20, dot_y, 3)

    # Progress bar
    bar_w = int(WIDTH * 0.7)
    bar_h = 6 if not lo.scale_name else 10
    bx, by = cx - bar_w // 2, HEIGHT // 2 - 5
    display.set_pen(DIM)
    display.rectangle(bx, by, bar_w, bar_h)

    filled = int(bar_w * step / total_steps)
    if filled > 0:
        for x in range(0, filled, 4):
            w = min(4, filled - x)
            display.set_pen(_hsv_pen(x / bar_w, 0.8, 0.9))
            display.rectangle(bx + x, by + 1, w, bar_h - 2)

    # Status message
    scale = lo.scale_boot_msg
    display.set_pen(color if color else TEXT)
    sw = display.measure_text(message, scale=scale, spacing=1)
    display.text(message, cx - sw // 2, HEIGHT // 2 + 15, -1, scale=scale, spacing=1)
    _flush()


# ─── Main display components ─────────────────────────────────────

def _draw_header(t):
    """Draw date header with rainbow accent line."""
    lo = layout
    date_str = "{} {} {}".format(today_day, month_name(today_month), today_year)

    display.set_pen(HEADER_BG)
    display.rectangle(0, 0, WIDTH, lo.header_h)

    scale = lo.scale_title
    tw = display.measure_text(date_str, scale=scale, spacing=1)
    tx = WIDTH // 2 - tw // 2
    ty = (lo.header_h - 8 * scale) // 2

    # Colored shadow (TFT only)
    if not IS_EINK:
        display.set_pen(_hsv_pen((t * 0.03) % 1.0, 0.7, 0.6))
        display.text(date_str, tx + 2, ty + 2, -1, scale=scale, spacing=1)
    display.set_pen(TEXT)
    display.text(date_str, tx, ty, -1, scale=scale, spacing=1)

    # Accent line
    line_y = lo.header_h - 3
    line_w = WIDTH - lo.margin * 2
    if IS_EINK:
        display.set_pen(TEXT)
        display.rectangle(lo.margin, line_y, line_w, 1)
    else:
        thickness = 3 if lo.scale_name else 2
        for x in range(0, line_w, 4):
            w = min(4, line_w - x)
            display.set_pen(_hsv_pen((x / line_w + t * 0.03) % 1.0, 0.8, 0.9))
            display.rectangle(lo.margin + x, line_y, w, thickness)


def _draw_timescale(year, t):
    """Draw the 'X years ago' label and timeline bar. Returns height used."""
    if year is None:
        return 0
    lo = layout
    years_ago = max(0, today_year - year)
    ts_range = today_year - TIMESCALE_START_YEAR

    y_top = lo.header_h + 8
    bar_x = lo.margin
    bar_w = WIDTH - lo.margin * 2

    # "il y a X ans" label
    display.set_pen(TEXT)
    display.text(years_ago_str(years_ago), bar_x, y_top, -1, scale=lo.scale_ago, spacing=1)

    # Timeline bar
    bar_y = y_top + 8 * lo.scale_ago + 2
    bar_h = 6
    display.set_pen(TIMESCALE_BG)
    display.rectangle(bar_x, bar_y, bar_w, bar_h)

    # Era tick marks (0 AD, 1000, 2000)
    display.set_pen(DIM)
    for mark in (0, 1000, 2000):
        if TIMESCALE_START_YEAR < mark < today_year:
            mx = bar_x + int(bar_w * (mark - TIMESCALE_START_YEAR) / ts_range)
            display.rectangle(mx, bar_y - 2, 1, bar_h + 4)

    # Rainbow fill from event year to now
    event_ratio = max(0.0, min(1.0, (year - TIMESCALE_START_YEAR) / ts_range))
    fill_x = bar_x + int(bar_w * event_ratio)
    fill_w = bar_x + bar_w - fill_x
    if fill_w > 0:
        for x in range(0, fill_w, 4):
            w = min(4, fill_w - x)
            display.set_pen(_hsv_pen((x / max(1, bar_w) * 0.7 + t * 0.02) % 1.0, 0.7, 0.8))
            display.rectangle(fill_x + x, bar_y + 1, w, bar_h - 2)

    # Marker dot
    display.set_pen(_hsv_pen((t * 0.03) % 1.0, 0.8, 1.0))
    display.circle(max(fill_x, bar_x + 4), bar_y + bar_h // 2, 4)

    return lo.timescale_h


def _draw_event(events, idx, t, alpha=1.0):
    """Draw a single event: year, title, body text."""
    if not events:
        display.set_pen(DIM)
        msg = s("no_events")
        mw = display.measure_text(msg, scale=layout.scale_title, spacing=1)
        display.text(msg, WIDTH // 2 - mw // 2, HEIGHT // 2 - 16, -1, scale=layout.scale_title, spacing=1)
        return

    lo = layout
    ev = Event(events[idx])
    body_width = WIDTH - lo.margin * 2
    hue_base = (t * 0.02 + idx * 0.15) % 1.0

    # Timescale
    ts_h = _draw_timescale(ev.year, t)
    y = lo.header_h + 8 + ts_h + 4
    bottom = HEIGHT - 6

    # Year
    if ev.year is not None:
        scale = lo.scale_year
        year_str = str(ev.year)
        year_w = display.measure_text(year_str, scale=scale, spacing=1)

        if IS_EINK:
            display.set_pen(TEXT)
        elif ev.is_birth:
            display.set_pen(BIRTH_PEN)
        else:
            display.set_pen(_hsv_pen(hue_base, 0.7, alpha))
        display.text(year_str, lo.margin, y, -1, scale=scale, spacing=1)

        # Decorative dash (large screens)
        if lo.scale_name:
            display.set_pen(_hsv_pen(hue_base + 0.3, 0.5, 0.6 * alpha))
            display.rectangle(lo.margin + year_w + 10, y + 4 * scale, 40, 3)
        y += lo.line_height(scale) + 6

    # Title (large screens only — scale_name=0 means skip)
    if ev.title and lo.scale_name:
        scale = lo.scale_name
        truncated = ev.title
        while display.measure_text(truncated, scale=scale, spacing=1) > body_width and len(truncated) > 10:
            truncated = truncated[:-4] + "..."

        if IS_EINK:
            display.set_pen(TEXT)
        elif ev.is_birth:
            display.set_pen(BIRTH_PEN)
        else:
            display.set_pen(_hsv_pen(hue_base + 0.15, 0.5, 0.9 * alpha))
        display.text(truncated, lo.margin, y, -1, scale=scale, spacing=1)
        y += lo.line_height(scale) + 2

    # Body text — try larger scale first, fall back to smaller
    available = bottom - y
    scale = lo.scale_body
    lines = _word_wrap(ev.text, body_width, scale)
    lh = lo.line_height(scale)

    if len(lines) * lh > available:
        scale = lo.scale_body_small
        lines = _word_wrap(ev.text, body_width, scale)
        lh = lo.line_height(scale)

    max_lines = max(1, available // lh)
    truncated = len(lines) > max_lines
    if truncated:
        lines = lines[:max_lines]

    display.set_pen(TEXT)
    for line in lines:
        display.text(line, lo.margin, y, -1, scale=scale, spacing=1)
        y += lh
    if truncated:
        display.set_pen(DIM)
        display.text("...", lo.margin + 8, y, -1, scale=scale, spacing=1)


def _draw_icon(events, idx, icon_loader):
    """Draw emoji icon in the bottom-right (large screens only)."""
    sz = layout.icon_size
    if not sz or not events or not icon_loader:
        return
    ev = Event(events[idx])
    if ev.icons:
        icon_loader.draw(ev.icons[0], WIDTH - layout.margin - sz - 4, HEIGHT - sz - 4)


def _update_leds(t):
    """Gentle rainbow LED glow (Presto only)."""
    if not presto:
        return
    for i in range(7):
        hue = (i / 7.0 + t * 0.03) % 1.0
        brightness = 0.12 + math.sin(t * 0.3 + i * 0.9) * 0.06
        presto.set_led_hsv(i, hue, 0.5, max(0.0, brightness))


# ─── Full frame rendering ───────────────────────────────────────

def draw_frame(events, idx, t, icon_loader, fade=1.0):
    """Render a complete frame. fade=0..1 for transition effect."""
    if presto:
        display.set_layer(0)

    # Background (with fade on TFT)
    if not IS_EINK and fade < 1.0 and _fade_bgs:
        display.set_pen(_fade_bgs[max(0, min(10, int(fade * 10)))])
    else:
        display.set_pen(BG)
    display.clear()

    # Content (skip during deep fade)
    if fade > 0.3 or IS_EINK:
        _draw_header(t)
        _draw_event(events, idx, t, alpha=fade if not IS_EINK else 1.0)
        _draw_icon(events, idx, icon_loader)
    _update_leds(t)
    _flush()
