"""Current screen — live gateway + internet metrics."""

import theme


def _fmt_ms(v):
    if v is None:
        return "--"
    if v >= 100:
        return "{:d}".format(int(round(v)))
    return "{:.0f}".format(v)


def _fmt_loss(v):
    if v is None:
        return "0%"
    return "{:.0f}%".format(v)


def _fmt_jit(v):
    if v is None:
        return "--"
    return "{:.1f}ms".format(v)


def _fmt_dns(v):
    if v is None:
        return "--"
    return "{:d}ms".format(int(round(v)))


def _fmt_rssi(v):
    if v is None:
        return "--dBm"
    return "{:d}dBm".format(int(v))


def _draw_channel(display, y_top, height, name, channel):
    """Draw one channel block (gateway or internet)."""
    pad = theme.PADDING_X
    status = channel["status"]
    metric_status = channel["metric_status"]

    # ── Title row ──────────────────────────────────────────────────
    title = "> " + name
    display.set_pen(theme.pen(display, theme.FG))
    display.text(title, pad, y_top + 4, scale=theme.SCALE_BODY)
    title_w = display.measure_text(title, scale=theme.SCALE_BODY)

    target = channel["target"]
    display.set_pen(theme.pen(display, theme.DIM))
    display.text(target, pad + title_w + 10, y_top + 4, scale=theme.SCALE_BODY)

    # Status pill on the right
    theme.status_pill(display, theme.WIDTH - pad, y_top + 2, status, height=22)

    # ── Hero latency ───────────────────────────────────────────────
    hero = _fmt_ms(channel["latency_ms"])
    hero_y = y_top + 30
    display.set_pen(theme.pen(display, theme.status_colour(metric_status.get("latency", "ok"))))
    display.text(hero, pad, hero_y, scale=theme.SCALE_HERO)
    hero_w = display.measure_text(hero, scale=theme.SCALE_HERO)

    # "ms" suffix
    display.set_pen(theme.pen(display, theme.DIM))
    display.text("ms", pad + hero_w + 6,
                 hero_y + (8 * (theme.SCALE_HERO - theme.SCALE_BODY)),
                 scale=theme.SCALE_BODY)

    # ── Secondary metrics, two columns ────────────────────────────
    col1_x = pad + 220
    col2_x = pad + 340
    line_y0 = y_top + 36
    line_y1 = y_top + 36 + 28

    rows = [
        ("loss", "loss " + _fmt_loss(channel["loss_pct"]),  metric_status.get("loss", "ok"),  col1_x, line_y0),
        ("dns",  "dns  " + _fmt_dns(channel["dns_ms"]),     metric_status.get("dns",  "ok"),  col2_x, line_y0),
        ("jit",  "jit  " + _fmt_jit(channel["jitter_ms"]),  metric_status.get("jitter","ok"), col1_x, line_y1),
        ("rssi", "rssi " + _fmt_rssi(channel["rssi_dbm"]),  metric_status.get("rssi", "ok"),  col2_x, line_y1),
    ]
    for _, label, st, x, ly in rows:
        display.set_pen(theme.pen(display, theme.status_colour(st)))
        display.text(label, x, ly, scale=theme.SCALE_BODY)


def draw(display, sampler):
    """Render the Current screen."""
    latest = sampler.latest

    body_top = theme.BODY_TOP
    body_bot = theme.BODY_BOTTOM
    body_h = body_bot - body_top

    block_h = (body_h - 4) // 2     # 4px gap for the dashed divider
    gw_y = body_top
    net_y = body_top + block_h + 4

    _draw_channel(display, gw_y, block_h, "GATEWAY",  latest["gateway"])
    theme.dashed_hline(display, gw_y + block_h + 1)
    _draw_channel(display, net_y, block_h, "INTERNET", latest["internet"])
