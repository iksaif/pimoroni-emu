"""Crash screen — displays unhandled exceptions on the display."""

import time


def show_crash(display, presto, err):
    """Show an error on screen and halt."""
    try:
        import sys
        sys.print_exception(err)
    except Exception:
        pass
    try:
        red = display.create_pen(255, 50, 50)
        white = display.create_pen(255, 255, 255)
        black = display.create_pen(0, 0, 0)
        _, height = display.get_bounds()
        display.set_pen(black)
        display.clear()
        display.set_pen(red)
        display.text("CRASH", 20, 20, -1, scale=4, spacing=1)
        display.set_pen(white)
        msg = str(err)
        y = 70
        for i in range(0, len(msg), 40):
            if y > height - 30:
                break
            display.text(msg[i:i + 40], 20, y, -1, scale=2, spacing=1)
            y += 22
        if presto:
            presto.update()
        else:
            display.update()
    except Exception:
        pass
    while True:
        time.sleep(1)
