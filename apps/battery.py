"""Battery display app that works on all device types.

Shows a battery icon with fill level and color based on charge.
Use the voltage slider in the emulator sensor panel to change the level.
"""

# Check emulator state for device type
try:
    from emulator import get_state
    device = get_state().get("device")
    device_name = device.name if device else "Unknown"
    library_type = getattr(device, 'library_type', 'picographics')
except ImportError:
    device_name = "Unknown"
    library_type = "picographics"


def get_level():
    """Get battery level (0-100) from the battery mock."""
    battery = get_state().get("battery")
    if battery:
        return battery.get_level()
    return 50


def get_charging():
    """Check if battery is currently charging."""
    battery = get_state().get("battery")
    if battery:
        return battery._charging
    return False


def level_color_rgb(level):
    """Return (r, g, b) based on charge level."""
    if level > 60:
        return (0, 200, 0)
    elif level > 30:
        return (255, 180, 0)
    else:
        return (220, 0, 0)


if library_type == 'inky':
    from inky.auto import auto
    from PIL import Image, ImageDraw, ImageFont

    inky = auto(ask_user=True, verbose=True)
    img = Image.new("RGB", (inky.width, inky.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    level = get_level()
    r, g, b = level_color_rgb(level)

    # Battery icon dimensions
    bw, bh = 200, 100
    bx = (inky.width - bw) // 2
    by = (inky.height - bh) // 2 - 20
    tip_w, tip_h = 12, 40

    # Outline
    draw.rectangle([bx, by, bx + bw, by + bh], outline=(0, 0, 0), width=4)
    # Tip
    draw.rectangle([bx + bw, by + (bh - tip_h) // 2,
                     bx + bw + tip_w, by + (bh + tip_h) // 2],
                    fill=(0, 0, 0))
    # Fill
    pad = 6
    fill_w = int((bw - pad * 2) * level / 100)
    if fill_w > 0:
        draw.rectangle([bx + pad, by + pad, bx + pad + fill_w, by + bh - pad],
                        fill=(r, g, b))

    # Charging indicator (lightning bolt)
    charging = get_charging()
    if charging:
        cx = bx + bw // 2
        cy = by + bh // 2
        bolt = [(cx + 5, by + 8), (cx - 5, cy + 2), (cx + 2, cy + 2),
                (cx - 5, by + bh - 8), (cx + 5, cy - 2), (cx - 2, cy - 2)]
        draw.polygon(bolt, fill=(255, 200, 0))

    # Label
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    text = f"{level}%"
    if charging:
        text += " CHG"
    bbox = draw.textbbox((0, 0), text, font=font)
    tx = (inky.width - (bbox[2] - bbox[0])) // 2
    draw.text((tx, by + bh + 15), text, (0, 0, 0), font=font)

    inky.set_image(img)
    inky.show()

elif library_type == 'badgeware':
    from badgeware import run

    def update():
        level = get_level()
        r, g, b = level_color_rgb(level)

        screen.pen = color.rgb(0, 0, 0)
        screen.clear()

        # Battery outline (fits 39x26 display)
        # Body: 5,6 to 32,20  Tip: 32,10 to 34,16
        bx, by, bw, bh = 5, 6, 27, 14
        screen.pen = color.rgb(255, 255, 255)
        # Top edge
        for x in range(bx, bx + bw + 1):
            screen.pixel(x, by)
        # Bottom edge
        for x in range(bx, bx + bw + 1):
            screen.pixel(x, by + bh)
        # Left edge
        for y in range(by, by + bh + 1):
            screen.pixel(bx, y)
        # Right edge
        for y in range(by, by + bh + 1):
            screen.pixel(bx + bw, y)
        # Tip
        for y in range(by + 4, by + bh - 3):
            screen.pixel(bx + bw + 1, y)
            screen.pixel(bx + bw + 2, y)

        # Fill
        screen.pen = color.rgb(r, g, b)
        fill_w = max(0, int((bw - 2) * level / 100))
        for fy in range(by + 1, by + bh):
            for fx in range(bx + 1, bx + 1 + fill_w):
                screen.pixel(fx, fy)

        # Charging indicator (small lightning bolt inside battery)
        charging = get_charging()
        if charging:
            screen.pen = color.rgb(255, 200, 0)
            cx = bx + bw // 2
            # Simple vertical bolt: 3 pixels wide
            for y in range(by + 2, by + bh - 1):
                screen.pixel(cx, y)
            screen.pixel(cx - 1, by + 4)
            screen.pixel(cx + 1, by + bh - 5)

        # Percentage text
        screen.pen = color.rgb(255, 255, 255)
        screen.font = rom_font.winds
        text = f"{level}%"
        if charging:
            text += " CHG"
        tw, th = screen.measure_text(text)
        screen.text(text, (screen.width - tw) // 2, 0)

    run(update)

elif "presto" in device_name.lower():
    from presto import Presto
    import time

    presto = Presto()
    display = presto.display
    WIDTH, HEIGHT = display.get_bounds()

    while True:
        level = get_level()
        r, g, b = level_color_rgb(level)

        display.set_pen(display.create_pen(0, 0, 0))
        display.clear()

        # Battery icon
        bw, bh = 240, 120
        bx = (WIDTH - bw) // 2
        by = HEIGHT // 2 - bh // 2 - 20
        tip_w, tip_h = 14, 50

        # Outline
        WHITE = display.create_pen(255, 255, 255)
        display.set_pen(WHITE)
        display.rectangle(bx, by, bw, 4)
        display.rectangle(bx, by + bh - 4, bw, 4)
        display.rectangle(bx, by, 4, bh)
        display.rectangle(bx + bw - 4, by, 4, bh)
        # Tip
        display.rectangle(bx + bw, by + (bh - tip_h) // 2, tip_w, tip_h)

        # Fill
        pad = 8
        fill_w = int((bw - pad * 2) * level / 100)
        if fill_w > 0:
            display.set_pen(display.create_pen(r, g, b))
            display.rectangle(bx + pad, by + pad, fill_w, bh - pad * 2)

        # Charging indicator (lightning bolt inside battery)
        charging = get_charging()
        if charging:
            YELLOW = display.create_pen(255, 200, 0)
            display.set_pen(YELLOW)
            cx = bx + bw // 2
            cy = by + bh // 2
            # Draw bolt as rectangles
            display.rectangle(cx - 2, by + 15, 12, 4)     # top arm
            display.rectangle(cx + 2, by + 19, 4, bh - 50)  # middle
            display.rectangle(cx - 6, cy + 4, 12, 4)      # bottom arm

        # Percentage text
        display.set_pen(WHITE)
        display.set_font("bitmap8")
        text = f"{level}%"
        if charging:
            text += " CHG"
        display.text(text, bx, by + bh + 20, WIDTH, 4)

        display.update()
        presto.update()
        time.sleep(0.1)

else:
    from picographics import PicoGraphics
    import time

    if "tufty" in device_name.lower():
        from picographics import DISPLAY_TUFTY_2350
        display = PicoGraphics(display=DISPLAY_TUFTY_2350)
    elif "badger" in device_name.lower():
        from picographics import DISPLAY_BADGER_2350
        display = PicoGraphics(display=DISPLAY_BADGER_2350)
    else:
        from picographics import DISPLAY_TUFTY_2350
        display = PicoGraphics(display=DISPLAY_TUFTY_2350)

    WIDTH, HEIGHT = display.get_bounds()
    WHITE = display.create_pen(255, 255, 255)
    BLACK = display.create_pen(0, 0, 0)

    while True:
        level = get_level()
        r, g, b = level_color_rgb(level)

        display.set_pen(WHITE)
        display.clear()

        # Battery icon
        bw, bh = 180, 90
        bx = (WIDTH - bw) // 2
        by = HEIGHT // 2 - bh // 2 - 15
        tip_w, tip_h = 10, 36

        # Outline
        display.set_pen(BLACK)
        display.rectangle(bx, by, bw, 3)
        display.rectangle(bx, by + bh - 3, bw, 3)
        display.rectangle(bx, by, 3, bh)
        display.rectangle(bx + bw - 3, by, 3, bh)
        # Tip
        display.rectangle(bx + bw, by + (bh - tip_h) // 2, tip_w, tip_h)

        # Fill
        pad = 6
        fill_w = int((bw - pad * 2) * level / 100)
        if fill_w > 0:
            display.set_pen(display.create_pen(r, g, b))
            display.rectangle(bx + pad, by + pad, fill_w, bh - pad * 2)

        # Charging indicator (lightning bolt inside battery)
        charging = get_charging()
        if charging:
            YELLOW = display.create_pen(255, 200, 0)
            display.set_pen(YELLOW)
            cx = bx + bw // 2
            cy = by + bh // 2
            # Draw bolt as rectangles
            display.rectangle(cx - 2, by + 10, 10, 3)      # top arm
            display.rectangle(cx + 1, by + 13, 3, bh - 36)  # middle
            display.rectangle(cx - 5, cy + 3, 10, 3)       # bottom arm

        # Percentage text
        display.set_pen(BLACK)
        display.set_font("bitmap8")
        text = f"{level}%"
        if charging:
            text += " CHG"
        display.text(text, bx, by + bh + 10, WIDTH, 3)

        display.update()
        time.sleep(0.1)
