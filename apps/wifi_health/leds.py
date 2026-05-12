"""Per-LED patterns for the Presto's 7 back-edge SK6812 LEDs.

The LEDs are arranged around the display edge, anticlockwise starting at
the top-left:
    0  top-left
    1  left
    2  bottom-left
    3  bottom-centre
    4  bottom-right
    5  right
    6  top-right

Each screen renders a pattern that maps the screen's content to the ring
so the device gives an at-a-glance health read even when you're not
looking directly at the LCD.
"""

import time

import theme


def _dim(rgb, factor):
    return tuple(int(c * factor) for c in rgb)


def for_current(sampler):
    """Left half (3 LEDs) = gateway, bottom-centre = DNS, right half = internet.

    Geographic split matches the on-screen layout: gateway on top, internet
    below, DNS shared.
    """
    latest = sampler.latest
    gw_col  = theme.status_colour(latest["gateway"]["status"])
    nt_col  = theme.status_colour(latest["internet"]["status"])
    dns_col = theme.status_colour(
        latest["gateway"]["metric_status"].get("dns", "ok")
    )
    return [gw_col, gw_col, gw_col, dns_col, nt_col, nt_col, nt_col]


def for_log(sampler):
    """Show the seven most recent NET slot statuses, oldest-left, newest-right."""
    slots = sampler.slots_snapshot()
    last7 = slots[-7:]
    return [theme.status_colour(s.get("net", "down")) for s in last7]


def for_settings():
    """Calm 4-second dim-green breath while the user fiddles with options."""
    phase = (time.time() % 4.0) / 4.0          # 0 → 1
    breath = 0.3 + 0.7 * (1 - abs(phase * 2 - 1))   # triangle wave 0.3..1.0
    return [_dim(theme.DIM, breath)] * 7


def alarm(sampler):
    """When the channel is fully down, override with a 1 Hz red flash."""
    gw = sampler.latest["gateway"]["status"]
    nt = sampler.latest["internet"]["status"]
    if gw != "down" or nt != "down":
        return None  # caller falls back to the per-screen pattern
    on = (time.time() % 1.0) < 0.5
    return [theme.DOWN if on else (0, 0, 0)] * 7


def pattern_for(screen, sampler):
    """Pick the right pattern for the active screen."""
    flash = alarm(sampler)
    if flash is not None:
        return flash
    if screen == "current":
        return for_current(sampler)
    if screen == "log":
        return for_log(sampler)
    return for_settings()
