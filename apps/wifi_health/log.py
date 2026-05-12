"""Log / 24h screen — heatmaps + ping plot."""

import time

import theme


HEATMAP_GAP     = 2


def _status_pen(display, status, dimmed=False):
    if status == "none":
        rgb = theme.SCAN          # very dim — visually "no data"
    else:
        rgb = theme.status_colour(status)
    if dimmed:
        rgb = tuple(c // 2 for c in rgb)
    return theme.pen(display, rgb)


def _draw_heatmap_row(display, label, statuses, x, y, w, h, open_idx):
    display.set_pen(theme.pen(display, theme.FG))
    display.text(label, x, y + (h - 8 * theme.SCALE_BODY) // 2,
                 scale=theme.SCALE_BODY)

    cells_x = x + theme.ROW_LABEL_W
    cells_w = w - theme.ROW_LABEL_W
    n = len(statuses)
    cell_w = cells_w / n
    for i, st in enumerate(statuses):
        cx = int(cells_x + i * cell_w)
        cw = int(cells_x + (i + 1) * cell_w) - cx - 1
        if cw < 1:
            cw = 1
        dim = (i == open_idx)
        display.set_pen(_status_pen(display, st, dimmed=dim))
        display.rectangle(cx, y, cw, h)


def _draw_time_axis(display, x, y, w):
    display.set_pen(theme.pen(display, theme.DIM))
    now = time.localtime()
    now_label = "{:02d}:{:02d}".format(now[3], now[4])
    # Labels: now-24h, now-20h, ..., now
    ticks = [now_label, "20", "16", "12", "08", "04", now_label]
    n = len(ticks)
    cells_x = x + theme.ROW_LABEL_W
    cells_w = w - theme.ROW_LABEL_W
    for i, t in enumerate(ticks):
        tx = int(cells_x + (cells_w / (n - 1)) * i)
        tw = display.measure_text(t, scale=theme.SCALE_BODY)
        # Anchor middle ticks centered; left-/right-most aligned to edge
        if i == 0:
            x_text = tx
        elif i == n - 1:
            x_text = tx - tw
        else:
            x_text = tx - tw // 2
        display.text(t, x_text, y, scale=theme.SCALE_BODY)


def _draw_ping_plot(display, samples, x, y, w, h):
    # Frame label
    display.set_pen(theme.pen(display, theme.DIM))
    display.text("NET PING . ms", x, y, scale=theme.SCALE_BODY)
    plot_y = y + 8 * theme.SCALE_BODY + 6
    plot_h = h - (8 * theme.SCALE_BODY + 6)
    if plot_h < 20:
        return

    # Gridlines at 100ms (y=33%) and 200ms (y=66%) of plot_h
    max_ms = 250.0
    for ms in (100, 200):
        gy = plot_y + int(plot_h - (ms / max_ms) * plot_h)
        theme.dashed_hline(display, gy, x0=x + 28, x1=x + w, on=3, off=4, colour=theme.DIM)
        display.set_pen(theme.pen(display, theme.DIM))
        display.text(str(ms), x, gy - 4, scale=theme.SCALE_TINY)

    # Plot line
    if not samples:
        return
    display.set_pen(theme.pen(display, theme.FG))
    n = len(samples)
    plot_x0 = x + 28
    plot_w = w - 28
    last_pt = None
    for i, ms in enumerate(samples):
        if ms is None:
            # Outage marker: vertical red bar
            display.set_pen(theme.pen(display, theme.DOWN))
            px = plot_x0 + int(plot_w * i / max(1, n - 1))
            display.rectangle(px, plot_y, 1, plot_h)
            display.set_pen(theme.pen(display, theme.FG))
            last_pt = None
            continue
        ms_clamped = ms if ms < max_ms else max_ms
        py = plot_y + int(plot_h - (ms_clamped / max_ms) * plot_h)
        px = plot_x0 + int(plot_w * i / max(1, n - 1))
        if last_pt is not None:
            _line(display, last_pt[0], last_pt[1], px, py)
        last_pt = (px, py)


def _line(display, x0, y0, x1, y1):
    """Thin 1px line."""
    display.line(x0, y0, x1, y1)


def draw(display, sampler):
    body_top = theme.BODY_TOP + 8
    pad = theme.PADDING_X
    content_w = theme.WIDTH - 2 * pad

    # Subtitle
    display.set_pen(theme.pen(display, theme.DIM))
    display.text("last 24h . rolling . 30min/cell", pad, body_top, scale=theme.SCALE_BODY)
    cursor = body_top + 8 * theme.SCALE_BODY + 8

    # Heatmaps
    slots = sampler.slots_snapshot()
    gw_statuses  = [s.get("gw", "down") for s in slots]
    net_statuses = [s.get("net", "down") for s in slots]
    # Highlight the open (live) slot
    open_idx = -1
    for i, s in enumerate(slots):
        if s.get("open"):
            open_idx = i
    _draw_heatmap_row(display, "GW",  gw_statuses,  pad, cursor, content_w, theme.HEATMAP_CELL_H, open_idx)
    cursor += theme.HEATMAP_CELL_H + HEATMAP_GAP
    _draw_heatmap_row(display, "NET", net_statuses, pad, cursor, content_w, theme.HEATMAP_CELL_H, open_idx)
    cursor += theme.HEATMAP_CELL_H + 6

    # Time axis
    _draw_time_axis(display, pad, cursor, content_w)
    cursor += 8 * theme.SCALE_BODY + 10

    # Ping plot
    _draw_ping_plot(display, sampler.live_ping(), pad, cursor, content_w, theme.PLOT_HEIGHT)
    cursor += theme.PLOT_HEIGHT + 8

    # Summary line
    warn, down, uptime = sampler.stats()
    left_y = theme.BODY_BOTTOM - 8 * theme.SCALE_BODY - 6
    display.set_pen(theme.pen(display, theme.DIM))
    display.text("incidents:", pad, left_y, scale=theme.SCALE_BODY)
    incidents_x = pad + display.measure_text("incidents: ", scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.WARN if warn else theme.DIM))
    w_label = "{:d}w".format(warn)
    display.text(w_label, incidents_x, left_y, scale=theme.SCALE_BODY)
    incidents_x += display.measure_text(w_label + " . ", scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.DIM))
    display.text(". ", incidents_x - display.measure_text(". ", scale=theme.SCALE_BODY),
                 left_y, scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.DOWN if down else theme.DIM))
    display.text("{:d}d".format(down), incidents_x, left_y, scale=theme.SCALE_BODY)

    right_label = "uptime {:.1f}%".format(uptime)
    rw = display.measure_text(right_label, scale=theme.SCALE_BODY)
    display.set_pen(theme.pen(display, theme.FG if uptime >= 99 else theme.WARN if uptime >= 95 else theme.DOWN))
    display.text(right_label, theme.WIDTH - pad - rw, left_y, scale=theme.SCALE_BODY)
