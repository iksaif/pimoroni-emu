"""Simple demo for Inky Frame 7.3" (MicroPython/PicoGraphics)."""

from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7
from pimoroni import Button
import time

# Set up display (Spectra 6-color e-ink)
display = PicoGraphics(display=DISPLAY_INKY_FRAME_7)
WIDTH, HEIGHT = display.get_bounds()

# Set up buttons A-E
button_a = Button(0)
button_b = Button(1)
button_c = Button(2)
button_d = Button(3)
button_e = Button(4)

# Define Spectra 6 colors
BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)
GREEN = display.create_pen(0, 128, 0)
BLUE = display.create_pen(0, 0, 255)
RED = display.create_pen(255, 0, 0)
YELLOW = display.create_pen(255, 255, 0)

COLORS = [BLACK, WHITE, GREEN, BLUE, RED, YELLOW]
COLOR_NAMES = ["Black", "White", "Green", "Blue", "Red", "Yellow"]

current_bg = 1  # White background
current_fg = 0  # Black foreground


def draw_screen():
    """Draw the demo screen."""
    global current_bg, current_fg

    # Background
    display.set_pen(COLORS[current_bg])
    display.clear()

    # Draw color swatches
    swatch_w = WIDTH // 6
    swatch_h = 80
    y = 20

    for i, (color, name) in enumerate(zip(COLORS, COLOR_NAMES)):
        x = i * swatch_w
        display.set_pen(color)
        display.rectangle(x + 5, y, swatch_w - 10, swatch_h)

        # Label (in contrasting color)
        display.set_pen(WHITE if i in [0, 2, 3] else BLACK)
        display.set_font("bitmap8")
        display.text(name, x + 10, y + swatch_h + 10, scale=2)

    # Title
    display.set_pen(COLORS[current_fg])
    display.set_font("bitmap8")
    display.text("Inky Frame 7.3\" Demo", 20, HEIGHT // 2 - 40, scale=4)
    display.text("Spectra 6-Color E-Ink Display", 20, HEIGHT // 2 + 20, scale=2)
    display.text(f"Resolution: {WIDTH}x{HEIGHT}", 20, HEIGHT // 2 + 60, scale=2)

    # Button hints
    display.text("A: Cycle BG  B: Cycle FG  C/D/E: More colors", 20, HEIGHT - 50, scale=2)

    display.update()


# Initial draw
draw_screen()
last_press = 0

# Main loop
while True:
    now = time.time()

    # Debounce (e-ink refresh takes time)
    if now - last_press > 2:
        if button_a.is_pressed():
            current_bg = (current_bg + 1) % len(COLORS)
            if current_bg == current_fg:
                current_bg = (current_bg + 1) % len(COLORS)
            draw_screen()
            last_press = now

        if button_b.is_pressed():
            current_fg = (current_fg + 1) % len(COLORS)
            if current_fg == current_bg:
                current_fg = (current_fg + 1) % len(COLORS)
            draw_screen()
            last_press = now

    time.sleep(0.1)
