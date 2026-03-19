"""Crash screen — displays unhandled exceptions on the display."""

import time


def show_crash(display, presto, err):
    """Show an error on screen and halt. Works with compat display wrapper."""
    try:
        import sys
        sys.print_exception(err)
    except Exception:
        pass
    try:
        red = display.create_pen(255, 50, 50)
        white = display.create_pen(255, 255, 255)
        black = display.create_pen(0, 0, 0)
        display.set_pen(black)
        display.clear()
        display.set_pen(red)
        display.text("CRASH", 20, 20, scale=4)
        display.set_pen(white)
        msg = str(err)
        y = 70
        for i in range(0, len(msg), 40):
            if y > display.height - 30:
                break
            display.text(msg[i:i + 40], 20, y, scale=2)
            y += 22
        display.update()
    except Exception:
        pass
    while True:
        time.sleep(1)
