"""CRT terminal theme for the WiFi Health Monitor.

Palette, drawing helpers (dashed lines, status pills, blinking cursor) and
the layout constants. All sizes are tuned for the Presto's 480x480 display.
"""

import time


# ─── Palette (CRT green-phosphor) ──────────────────────────────────────
BG     = (2, 6, 4)        # near-black with green tint
FG     = (52, 255, 122)   # bright phosphor green
DIM    = (29, 138, 68)    # secondary text, dividers, axis ticks
WARN   = (255, 204, 51)   # amber
DOWN   = (255, 80, 80)    # red
SCAN   = (12, 24, 16)     # very faint green for scanlines


# ─── Layout (Presto 480x480) ───────────────────────────────────────────
WIDTH         = 480
HEIGHT        = 480
HEADER_H      = 36
FOOTER_H      = 66
BODY_TOP      = HEADER_H
BODY_BOTTOM   = HEIGHT - FOOTER_H        # 414
PADDING_X     = 14
TAB_W         = WIDTH // 3               # 160

# Hero numbers, body text, axis ticks. We use built-in bitmap8 (5x8) and
# scale it up — that gives a tabular monospaced font that suits the CRT look
# without requiring a custom font upload.
SCALE_HERO    = 6       # ≈ 48px (matches the 54px design slot)
SCALE_TITLE   = 3       # ≈ 24px
SCALE_BODY    = 2       # ≈ 16px
SCALE_TINY    = 1       # ≈ 8px


_PEN_CACHE = {}


def pen(display, rgb):
    """Get a cached pen for an (r, g, b) colour tuple."""
    p = _PEN_CACHE.get(rgb)
    if p is None:
        p = display.create_pen(*rgb)
        _PEN_CACHE[rgb] = p
    return p


def clear_pen_cache():
    """Reset pens after a display recreation."""
    _PEN_CACHE.clear()


# ─── Drawing helpers ───────────────────────────────────────────────────


def dashed_hline(display, y, x0=PADDING_X, x1=WIDTH - PADDING_X,
                 on=4, off=6, colour=DIM):
    """Draw a dashed horizontal line. Pattern: `on` lit + `off` blank."""
    display.set_pen(pen(display, colour))
    x = x0
    period = on + off
    while x < x1:
        display.rectangle(x, y, min(on, x1 - x), 1)
        x += period


def dashed_vline(display, x, y0, y1, on=4, off=6, colour=DIM):
    """Draw a dashed vertical line."""
    display.set_pen(pen(display, colour))
    y = y0
    period = on + off
    while y < y1:
        display.rectangle(x, y, 1, min(on, y1 - y))
        y += period


def status_colour(status):
    """Map a status string to its palette colour."""
    if status == "ok":
        return FG
    if status == "warn":
        return WARN
    if status == "down":
        return DOWN
    return DIM


def status_glyph(status):
    """Map a status to its leading glyph (using ASCII fallbacks for bitmap8)."""
    if status == "ok":
        return "* OK"
    if status == "warn":
        return "^ WARN"
    if status == "down":
        return "x DOWN"
    return "? --"


def status_pill(display, x_right, y, status, height=28):
    """Draw a right-aligned status pill ending at x_right.

    Uses a 1px border in the status colour and ASCII glyphs (bitmap8 doesn't
    have the Unicode bullet/check characters from the design).
    """
    label = status_glyph(status)
    text_w = display.measure_text(label, scale=SCALE_BODY)
    pad_x = 8
    w = text_w + pad_x * 2
    x = x_right - w
    col = status_colour(status)
    # Border
    display.set_pen(pen(display, col))
    display.rectangle(x, y, w, 1)
    display.rectangle(x, y + height - 1, w, 1)
    display.rectangle(x, y, 1, height)
    display.rectangle(x + w - 1, y, 1, height)
    # Label
    text_y = y + (height - 8 * SCALE_BODY) // 2
    display.text(label, x + pad_x, text_y, scale=SCALE_BODY)
    return x  # left edge, so caller can position siblings


def cursor_visible():
    """Blinking cursor: 1Hz, 50% duty."""
    return (time.time() % 1.0) < 0.5


def scanlines(display, alpha_skip=4):
    """Optional CRT scanline overlay. Draws faint lines every `alpha_skip` rows."""
    display.set_pen(pen(display, SCAN))
    for y in range(0, HEIGHT, alpha_skip):
        display.rectangle(0, y, WIDTH, 1)


# ─── Tab footer ────────────────────────────────────────────────────────

TABS = [
    ("CURRENT", "current"),
    ("LOG 24H", "log"),
    ("CFG",     "settings"),
]


def draw_footer(display, active):
    """Draw the bottom tab strip and return the tab regions.

    Returns a list of (screen_key, x, y, w, h) so the main loop can hit-test.
    """
    y = BODY_BOTTOM
    # Top dashed divider
    dashed_hline(display, y, x0=0, x1=WIDTH)

    regions = []
    for i, (label, key) in enumerate(TABS):
        tx = i * TAB_W
        # Background — active tab gets a 1px box, inactive is bare
        if key == active:
            display.set_pen(pen(display, FG))
            display.rectangle(tx + 4, y + 6, TAB_W - 8, 1)              # top
            display.rectangle(tx + 4, y + FOOTER_H - 2, TAB_W - 8, 1)   # bottom
            display.rectangle(tx + 4, y + 6, 1, FOOTER_H - 8)            # left
            display.rectangle(tx + TAB_W - 5, y + 6, 1, FOOTER_H - 8)    # right
            colour = FG
        else:
            colour = DIM

        # Letter shortcut prefix (e.g. [A]) to mirror the hardware design
        prefix = "[{}]".format("ABC"[i])
        prefix_w = display.measure_text(prefix, scale=SCALE_BODY)
        label_w = display.measure_text(label, scale=SCALE_BODY)
        total_w = prefix_w + 6 + label_w
        x_text = tx + (TAB_W - total_w) // 2
        y_text = y + (FOOTER_H - 8 * SCALE_BODY) // 2

        display.set_pen(pen(display, FG if key == active else DIM))
        display.text(prefix, x_text, y_text, scale=SCALE_BODY)
        display.set_pen(pen(display, colour))
        display.text(label, x_text + prefix_w + 6, y_text, scale=SCALE_BODY)

        regions.append((key, tx, y, TAB_W, FOOTER_H))

    # Vertical dividers between tabs
    for i in range(1, len(TABS)):
        dashed_vline(display, i * TAB_W, y + 4, y + FOOTER_H - 4)

    return regions


def draw_header(display, mode_text, clock_text):
    """Draw the title bar with a blinking cursor and a right-aligned clock."""
    # Bottom border
    dashed_hline(display, HEADER_H - 1, x0=0, x1=WIDTH)
    # Mode text
    title = "> WIFI HEALTH . " + mode_text
    display.set_pen(pen(display, FG))
    display.text(title, PADDING_X, 6, scale=SCALE_BODY)
    title_w = display.measure_text(title, scale=SCALE_BODY)
    # Cursor block
    if cursor_visible():
        display.rectangle(PADDING_X + title_w + 4, 6, 10, 8 * SCALE_BODY)
    # Clock (dim, right-aligned)
    display.set_pen(pen(display, DIM))
    clock_w = display.measure_text(clock_text, scale=SCALE_BODY)
    display.text(clock_text, WIDTH - PADDING_X - clock_w, 6, scale=SCALE_BODY)
