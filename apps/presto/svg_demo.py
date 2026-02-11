"""SVG loading demo for PicoVector.

Loads an SVG file and renders it using PicoVector's polygon fill.
Demonstrates Polygon.from_svg() — an emulator extension.
"""

import time
from picographics import PicoGraphics, DISPLAY_PRESTO, PEN_RGB565
from picovector import PicoVector, Polygon, Transform

display = PicoGraphics(DISPLAY_PRESTO, pen_type=PEN_RGB565)
vector = PicoVector(display)

WIDTH, HEIGHT = display.get_bounds()

# Load SVG shapes separately for per-shape coloring
star = Polygon.from_svg("star.svg")
circle = Polygon.from_svg("circle.svg")
rect = Polygon.from_svg("rect.svg")

# Set up a transform to center and scale the SVGs
# All SVGs share a 200x200 viewBox; scale to fit display with margin
t = Transform()
scale = min(WIDTH, HEIGHT) / 200.0 * 0.8
t.translate(WIDTH / 2 - 100 * scale, HEIGHT / 2 - 100 * scale)
t.scale(scale)
vector.set_transform(t)

# Draw background
display.set_pen(display.create_pen(20, 20, 40))
display.clear()

# Draw each shape in a different color
display.set_pen(display.create_pen(255, 220, 50))
vector.draw(star)

display.set_pen(display.create_pen(255, 255, 255))
vector.draw(circle)

display.set_pen(display.create_pen(80, 200, 120))
vector.draw(rect)

display.update()

while True:
    time.sleep(0.1)
