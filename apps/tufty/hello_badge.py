"""Simple badge display for Tufty 2350."""

from picographics import PicoGraphics, DISPLAY_TUFTY_2350
from pimoroni import Button
import time

# Set up display
display = PicoGraphics(display=DISPLAY_TUFTY_2350)
WIDTH, HEIGHT = display.get_bounds()

# Set up buttons
button_a = Button(7)
button_b = Button(8)
button_c = Button(9)
button_up = Button(22)
button_down = Button(6)

# Colors
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
RED = display.create_pen(255, 50, 50)
GREEN = display.create_pen(50, 255, 50)
BLUE = display.create_pen(50, 100, 255)

# Badge content
name = "Hello!"
title = "Pimoroni User"
bg_color = BLUE

def draw_badge():
    """Draw the badge content."""
    # Background
    display.set_pen(bg_color)
    display.clear()

    # White header bar
    display.set_pen(WHITE)
    display.rectangle(0, 0, WIDTH, 60)

    # Name
    display.set_pen(BLACK)
    display.set_font("bitmap8")
    display.text(name, 20, 20, scale=4)

    # Title
    display.set_pen(WHITE)
    display.text(title, 20, 80, scale=2)

    # Button hints at bottom
    display.set_pen(WHITE)
    display.text("A:Red  B:Green  C:Blue", 20, HEIGHT - 30, scale=1)

    display.update()

# Initial draw
draw_badge()

# Main loop
while True:
    if button_a.is_pressed():
        bg_color = RED
        draw_badge()

    if button_b.is_pressed():
        bg_color = GREEN
        draw_badge()

    if button_c.is_pressed():
        bg_color = BLUE
        draw_badge()

    time.sleep(0.1)
