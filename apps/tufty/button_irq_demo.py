"""Button IRQ demo - demonstrates hardware interrupt handling.

Shows how Pin.irq() handlers fire when buttons are pressed/released.
Press keyboard keys A, S, D or click the button indicators at the
bottom of the emulator window.

Run: pimoroni-emulator --device tufty apps/tufty/button_irq_demo.py
"""

import time
from machine import Pin
from picographics import PicoGraphics, DISPLAY_TUFTY_2350

display = PicoGraphics(display=DISPLAY_TUFTY_2350)
WIDTH, HEIGHT = display.get_bounds()

BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)
GREEN = display.create_pen(0, 220, 0)
RED = display.create_pen(220, 40, 40)
YELLOW = display.create_pen(220, 200, 0)
DARK_GRAY = display.create_pen(40, 40, 40)
BRIGHT_GREEN = display.create_pen(40, 255, 40)

# Button pins (Tufty 2350)
BUTTON_A_PIN = 7
BUTTON_B_PIN = 8
BUTTON_C_PIN = 9

pin_a = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
pin_b = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
pin_c = Pin(BUTTON_C_PIN, Pin.IN, Pin.PULL_UP)

# Track button events via IRQ
press_count = {"A": 0, "B": 0, "C": 0}
button_held = {"A": False, "B": False, "C": False}
events = []
MAX_EVENTS = 6


def make_handler(name):
    def handler(pin):
        val = pin.value()
        if val == 0:
            # Falling edge = pressed
            press_count[name] += 1
            button_held[name] = True
            events.append(f"[IRQ] {name} pressed  #{press_count[name]}")
        else:
            # Rising edge = released
            button_held[name] = False
            events.append(f"[IRQ] {name} released #{press_count[name]}")
        if len(events) > MAX_EVENTS:
            events.pop(0)
    return handler


pin_a.irq(handler=make_handler("A"), trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
pin_b.irq(handler=make_handler("B"), trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
pin_c.irq(handler=make_handler("C"), trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)


def draw():
    display.set_pen(BLACK)
    display.clear()

    display.set_font("bitmap8")

    # Title
    display.set_pen(WHITE)
    display.text("Pin.irq() Demo", 10, 8, scale=3)

    # Instructions
    display.set_pen(YELLOW)
    display.text("Keys: A  S  D  |  or click buttons below", 10, 42, scale=1)

    # Button state boxes - large, color-coded
    box_w = 90
    box_h = 60
    gap = 10
    start_x = (WIDTH - 3 * box_w - 2 * gap) // 2
    y = 60

    for i, name in enumerate(("A", "B", "C")):
        bx = start_x + i * (box_w + gap)
        held = button_held[name]
        count = press_count[name]

        # Box background: bright green when held, dark gray otherwise
        display.set_pen(BRIGHT_GREEN if held else DARK_GRAY)
        display.rectangle(bx, y, box_w, box_h)

        # Button label
        display.set_pen(BLACK if held else WHITE)
        display.text(name, bx + 38, y + 8, scale=3)

        # Press count
        display.set_pen(BLACK if held else GREEN)
        display.text(str(count), bx + 30, y + 42, scale=2)

    # Event log
    display.set_pen(WHITE)
    display.text("IRQ event log:", 10, 135, scale=1)

    log_y = 150
    for event in events:
        if "pressed" in event:
            display.set_pen(RED)
        else:
            display.set_pen(GREEN)
        display.text(event, 15, log_y, scale=1)
        log_y += 14

    display.update()


while True:
    draw()
    time.sleep(0.05)
