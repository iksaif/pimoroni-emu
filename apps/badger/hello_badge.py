"""Simple e-ink badge for Badger 2350."""

from picographics import PicoGraphics, DISPLAY_BADGER_2350
from pimoroni import Button
import time

# Set up display (e-ink)
display = PicoGraphics(display=DISPLAY_BADGER_2350)
WIDTH, HEIGHT = display.get_bounds()

# Set up buttons
button_a = Button(12)
button_b = Button(13)
button_c = Button(14)
button_up = Button(15)
button_down = Button(11)

# E-ink colors (black and white only)
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)

# Badge content options
badges = [
    {"name": "Alice", "title": "Developer", "company": "Pimoroni"},
    {"name": "Bob", "title": "Designer", "company": "Raspberry Pi"},
    {"name": "Charlie", "title": "Maker", "company": "Adafruit"},
]
badge_index = 0

def draw_badge():
    """Draw the badge content."""
    badge = badges[badge_index]

    # White background
    display.set_pen(WHITE)
    display.clear()

    # Black header bar
    display.set_pen(BLACK)
    display.rectangle(0, 0, WIDTH, 40)

    # Company name in header (inverted)
    display.set_pen(WHITE)
    display.set_font("bitmap8")
    display.text(badge["company"], 10, 12, scale=2)

    # Name (large)
    display.set_pen(BLACK)
    display.text(badge["name"], 10, 55, scale=4)

    # Title
    display.text(badge["title"], 10, 100, scale=2)

    # Navigation hint
    display.text("A/B: Change badge", 10, HEIGHT - 15, scale=1)

    display.update()

# Initial draw
draw_badge()
last_press = 0

# Main loop
while True:
    now = time.time()

    # Debounce
    if now - last_press > 0.5:
        if button_a.is_pressed():
            badge_index = (badge_index + 1) % len(badges)
            draw_badge()
            last_press = now

        if button_b.is_pressed():
            badge_index = (badge_index - 1) % len(badges)
            draw_badge()
            last_press = now

    time.sleep(0.1)
