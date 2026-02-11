"""PicoVector text demo - demonstrates .af font rendering.

Uses Alright Fonts (.af) vector font files to render text as polygons.
The font file must be in the same directory as this script.

Run: pimoroni-emulator --device presto apps/presto/vector_text_demo.py
"""

import math
import time

from picovector import ANTIALIAS_BEST, PicoVector, Polygon, Transform
from presto import Presto

presto = Presto()
display = presto.display
WIDTH, HEIGHT = display.get_bounds()

CX = WIDTH // 2
CY = HEIGHT // 2

# Colors
BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)
CYAN = display.create_pen(0, 200, 220)
ORANGE = display.create_pen(255, 160, 40)
PINK = display.create_pen(255, 100, 160)
GRAY = display.create_pen(80, 80, 80)

# PicoVector setup
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_BEST)
t = Transform()
vector.set_transform(t)

# Load font - try Roboto-Medium.af from vendor examples
vector.set_font("Roboto-Medium.af", 48)
vector.set_font_letter_spacing(100)
vector.set_font_word_spacing(200)

# Background shape
bg = Polygon()
bg.rectangle(0, 0, WIDTH, HEIGHT, (20, 20, 20, 20))

# Decorative circles
circle1 = Polygon()
circle1.circle(CX, CY, 180, 3)

tick = 0

while True:
    display.set_pen(BLACK)
    display.clear()

    # Decorative ring
    display.set_pen(GRAY)
    vector.set_transform(t)
    vector.draw(circle1)

    # Title - large
    display.set_pen(CYAN)
    vector.set_font_size(42)
    vector.text("PicoVector", 80, 80)

    # Subtitle
    display.set_pen(WHITE)
    vector.set_font_size(24)
    vector.text("Alright Fonts (.af) rendering", 60, 140)

    # Animated text
    y_offset = int(math.sin(tick / 10.0) * 8)
    display.set_pen(ORANGE)
    vector.set_font_size(36)
    vector.text("Hello World!", 100, 220 + y_offset)

    # Multi-line text
    display.set_pen(PINK)
    vector.set_font_size(20)
    vector.text("Line 1: Vector fonts\nLine 2: As polygons\nLine 3: Scalable!", 60, 300)

    # Small text
    display.set_pen(WHITE)
    vector.set_font_size(14)
    vector.text("abcdefghijklmnopqrstuvwxyz 0123456789", 30, 440)

    presto.update()
    tick += 1
    time.sleep(0.05)
