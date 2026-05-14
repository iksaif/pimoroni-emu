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


def _rssi_to_pct(dbm):
    """Map dBm to a 0..100% scale.

    -50 dBm or stronger → 100%, -100 dBm or weaker → 0%, linear between.
    Matches the bar-meter most operating systems show.
    """
    if dbm is None:
        return None
    pct = (dbm + 100) * 2
    if pct < 0:
        return 0
    if pct > 100:
        return 100
    return pct


def _fmt_signal(dbm):
    pct = _rssi_to_pct(dbm)
    if pct is None:
        return "--"
    return "{:d}%".format(int(pct))


def _draw_channel(display, y_top, height, name, channel):
    pad = theme.PADDING_X
    metric_status = channel["metric_status"]

    # ── Title row ──────────────────────────────────────────────────
    title = "> " + name
    display.set_pen(theme.pen(display, theme.FG))
    display.text(title, pad, y_top + 4, scale=theme.SCALE_BODY)
    title_w = display.measure_text(title, scale=theme.SCALE_BODY)

    gap_after_title = 10 if theme.DEVICE.has_touch else 6
    display.set_pen(theme.pen(display, theme.DIM))
    display.text(channel["target"], pad + title_w + gap_after_title,
                 y_top + 4, scale=theme.SCALE_BODY)

    # Pill is inset a few px from the right edge so it doesn't hug the
    # display border on small (Tufty) screens.
    pill_right = theme.WIDTH - pad - (0 if theme.DEVICE.has_touch else 4)
    theme.status_pill(display, pill_right, y_top + 2, channel["status"])

    # ── Hero latency ───────────────────────────────────────────────
    hero = _fmt_ms(channel["latency_ms"])
    hero_y = y_top + (28 if theme.DEVICE.has_touch else 20)
    display.set_pen(theme.pen(display, theme.status_colour(
        metric_status.get("latency", "ok"))))
    display.text(hero, pad, hero_y, scale=theme.SCALE_HERO)
    hero_w = display.measure_text(hero, scale=theme.SCALE_HERO)

    display.set_pen(theme.pen(display, theme.DIM))
    display.text("ms", pad + hero_w + 4,
                 hero_y + 8 * (theme.SCALE_HERO - theme.SCALE_BODY),
                 scale=theme.SCALE_BODY)

    # ── Secondary metrics ──────────────────────────────────────────
    # Gateway shows signal strength (it's local). Internet shows DNS time
    # (it's the upstream story). Each row has three metrics.
    if name == "GATEWAY":
        metrics = [
            ("loss " + _fmt_loss(channel["loss_pct"]),  metric_status.get("loss", "ok")),
            ("jit "  + _fmt_jit(channel["jitter_ms"]),  metric_status.get("jitter","ok")),
            ("sig "  + _fmt_signal(channel["rssi_dbm"]), metric_status.get("rssi", "ok")),
        ]
    else:
        metrics = [
            ("loss " + _fmt_loss(channel["loss_pct"]),  metric_status.get("loss", "ok")),
            ("dns "  + _fmt_dns(channel["dns_ms"]),     metric_status.get("dns",  "ok")),
            ("jit "  + _fmt_jit(channel["jitter_ms"]),  metric_status.get("jitter","ok")),
        ]

    if theme.DEVICE.has_touch:
        # Three metrics laid out as col1/col2 row1 + col1 row2 (the 4th
        # quadrant is intentionally blank now).
        col1_x, col2_x = pad + 220, pad + 340
        line_y0 = y_top + 36
        line_y1 = line_y0 + 28
        positions = [(col1_x, line_y0), (col2_x, line_y0), (col1_x, line_y1)]
        for (label, st), (x, ly) in zip(metrics, positions):
            display.set_pen(theme.pen(display, theme.status_colour(st)))
            display.text(label, x, ly, scale=theme.SCALE_BODY)
    else:
        # Tufty: 4 metrics on a single justified row beneath the hero.
        # Scale 1 here (8px) — scale 2 doesn't fit at 320px wide with all
        # four labels visible.
        metric_scale = theme.SCALE_TINY
        # Park the row well above the footer/divider so the text doesn't
        # crowd the [A] CURRENT button hints on the small Tufty screen.
        ly = y_top + height - 8 * metric_scale - 22
        widths = [display.measure_text(label, scale=metric_scale)
                  for label, _ in metrics]
        total_w = sum(widths)
        avail = theme.WIDTH - 2 * pad
        gap = max(4, (avail - total_w) // (len(metrics) - 1))
        x = pad
        for (label, st), w in zip(metrics, widths):
            display.set_pen(theme.pen(display, theme.status_colour(st)))
            display.text(label, x, ly, scale=metric_scale)
            x += w + gap


def draw(display, sampler):
    latest = sampler.latest

    body_h = theme.BODY_BOTTOM - theme.BODY_TOP
    block_h = (body_h - 4) // 2

    gw_y = theme.BODY_TOP
    net_y = theme.BODY_TOP + block_h + 4

    _draw_channel(display, gw_y, block_h, "GATEWAY",  latest["gateway"])
    theme.dashed_hline(display, gw_y + block_h + 1)
    _draw_channel(display, net_y, block_h, "INTERNET", latest["internet"])
