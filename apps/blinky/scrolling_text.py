"""Scrolling text for Blinky 2350 LED matrix."""

from picographics import PicoGraphics, DISPLAY_BLINKY
from pimoroni import Button
import time

# Set up display (LED matrix)
display = PicoGraphics(display=DISPLAY_BLINKY)
WIDTH, HEIGHT = display.get_bounds()

# Set up buttons
button_a = Button(7)
button_b = Button(8)

# Message to scroll
messages = [
    "Hello World! ",
    "Blinky 2350 ",
    "Pimoroni ",
]
message_index = 0
scroll_x = WIDTH

# Brightness levels (white LEDs)
def brightness_pen(level):
    """Create a pen with given brightness (0-255)."""
    return display.create_pen(level, level, level)

def draw_frame():
    """Draw one frame of scrolling text."""
    global scroll_x

    # Clear display
    display.set_pen(brightness_pen(0))
    display.clear()

    # Draw text
    display.set_pen(brightness_pen(255))
    display.set_font("bitmap8")
    text_width = display.measure_text(messages[message_index], scale=1)
    display.text(messages[message_index], int(scroll_x), 6, scale=1)

    # Scroll
    scroll_x -= 1
    if scroll_x < -text_width:
        scroll_x = WIDTH

    display.update()

# Main loop
frame = 0
while True:
    # Check buttons
    if button_a.is_pressed():
        message_index = (message_index + 1) % len(messages)
        scroll_x = WIDTH
        time.sleep(0.2)  # Debounce

    if button_b.is_pressed():
        message_index = (message_index - 1) % len(messages)
        scroll_x = WIDTH
        time.sleep(0.2)

    draw_frame()
    frame += 1
    time.sleep(0.05)  # ~20 FPS
