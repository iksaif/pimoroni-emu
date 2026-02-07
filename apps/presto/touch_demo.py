"""Touch demo for Presto."""

from presto import Presto
import time

# Initialize Presto
presto = Presto()
display = presto.display
WIDTH, HEIGHT = display.get_bounds()

# Colors
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
RED = display.create_pen(255, 80, 80)
GREEN = display.create_pen(80, 255, 80)
BLUE = display.create_pen(80, 80, 255)
YELLOW = display.create_pen(255, 255, 80)

# Button areas
buttons = [
    {"x": 40, "y": 40, "w": 180, "h": 180, "color": RED, "label": "RED"},
    {"x": 260, "y": 40, "w": 180, "h": 180, "color": GREEN, "label": "GREEN"},
    {"x": 40, "y": 260, "w": 180, "h": 180, "color": BLUE, "label": "BLUE"},
    {"x": 260, "y": 260, "w": 180, "h": 180, "color": YELLOW, "label": "YELLOW"},
]

# Current state
current_color = WHITE
touch_x, touch_y = 0, 0

def draw_screen():
    """Draw the main screen."""
    # Background
    display.set_pen(BLACK)
    display.clear()

    # Draw buttons
    for btn in buttons:
        display.set_pen(btn["color"])
        display.rectangle(btn["x"], btn["y"], btn["w"], btn["h"])

        # Button label
        display.set_pen(BLACK)
        display.set_font("bitmap8")
        display.text(btn["label"], btn["x"] + 50, btn["y"] + 80, scale=2)

    # Draw touch indicator
    if touch_x > 0 and touch_y > 0:
        display.set_pen(WHITE)
        display.circle(touch_x, touch_y, 10)

    # Status text
    display.set_pen(current_color)
    display.rectangle(150, 200, 180, 80)
    display.set_pen(BLACK)
    display.text("Touch a", 180, 220, scale=2)
    display.text("button!", 180, 250, scale=2)

    display.update()

def check_button_press(x, y):
    """Check if touch is within a button."""
    global current_color

    for btn in buttons:
        if (btn["x"] <= x < btn["x"] + btn["w"] and
            btn["y"] <= y < btn["y"] + btn["h"]):
            current_color = btn["color"]

            # Update RGB LEDs to match
            r = (current_color >> 16) & 0xFF
            g = (current_color >> 8) & 0xFF
            b = current_color & 0xFF
            presto.set_all_leds_rgb(r, g, b)
            presto.update_leds()
            return True

    return False

# Set initial LED color
presto.set_all_leds_rgb(255, 255, 255)
presto.update_leds()

# Initial draw
draw_screen()

# Main loop
while True:
    # Get touch state
    x, y, pressed = presto.touch()

    if pressed:
        touch_x, touch_y = x, y
        check_button_press(x, y)
        draw_screen()
    elif touch_x > 0:
        # Touch released
        touch_x, touch_y = 0, 0
        draw_screen()

    time.sleep(0.05)
