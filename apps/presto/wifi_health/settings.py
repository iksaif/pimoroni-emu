"""Settings screen — threshold profile, ping target, sample interval."""

import theme


SETTINGS_DEF = [
    {"key": "profile",  "label": "Threshold",       "values": ["LOOSE", "NORMAL", "STRICT"]},
    {"key": "target",   "label": "Ping target",     "values": ["1.1.1.1", "8.8.8.8", "9.9.9.9"]},
    {"key": "interval", "label": "Sample interval", "values": ["5s", "10s", "30s"]},
    {"key": "rssi_bar", "label": "Show RSSI bars",  "values": ["ON", "OFF"]},
    {"key": "bright",   "label": "Brightness",      "values": ["1", "2", "3", "4", "5"]},
]

DEFAULTS = {
    "profile": "NORMAL", "target": "1.1.1.1", "interval": "5s",
    "rssi_bar": "ON", "bright": "3",
}


class SettingsState:
    def __init__(self):
        self.values = dict(DEFAULTS)
        self.row_rects = []   # for hit-testing

    def cycle(self, key, direction=1):
        opts = next(s["values"] for s in SETTINGS_DEF if s["key"] == key)
        try:
            idx = opts.index(self.values[key])
        except ValueError:
            idx = 0
        self.values[key] = opts[(idx + direction) % len(opts)]


def draw(display, state):
    pad = theme.PADDING_X
    y = theme.BODY_TOP + 10
    row_h = 50

    state.row_rects = []

    for i, spec in enumerate(SETTINGS_DEF):
        # Row background hit-box
        state.row_rects.append((spec["key"], pad - 4, y, theme.WIDTH - 2 * pad + 8, row_h))

        # Label (dim)
        display.set_pen(theme.pen(display, theme.DIM))
        display.text(spec["label"], pad, y + (row_h - 8 * theme.SCALE_BODY) // 2,
                     scale=theme.SCALE_BODY)

        # Value (fg, right-aligned, drawn as `< VALUE >` to hint tappability)
        value = "< " + state.values[spec["key"]] + " >"
        vw = display.measure_text(value, scale=theme.SCALE_BODY)
        display.set_pen(theme.pen(display, theme.FG))
        display.text(value, theme.WIDTH - pad - vw,
                     y + (row_h - 8 * theme.SCALE_BODY) // 2,
                     scale=theme.SCALE_BODY)

        # Dashed divider
        theme.dashed_hline(display, y + row_h - 1)
        y += row_h

    # Hint
    hint = "tap value to cycle"
    hw = display.measure_text(hint, scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.DIM))
    display.text(hint, (theme.WIDTH - hw) // 2,
                 theme.BODY_BOTTOM - 8 * theme.SCALE_BODY - 8,
                 scale=theme.SCALE_BODY)


def hit_test(state, x, y):
    """Return the key of the row containing (x, y) or None."""
    for key, rx, ry, rw, rh in state.row_rects:
        if rx <= x < rx + rw and ry <= y < ry + rh:
            return key
    return None
