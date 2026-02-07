"""Temperature display app that works on all device types.

Uses the BME280 sensor (with slider control in the emulator UI).
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

# Initialize BME280 sensor (available on all MicroPython devices)
if library_type != 'inky':
    from pimoroni import PimoroniI2C
    from breakout_bme280 import BreakoutBME280

    i2c = PimoroniI2C()
    bme = BreakoutBME280(i2c)

def read_temp():
    """Read temperature from BME280 sensor."""
    if library_type == 'inky':
        return 22.5
    temperature, pressure, humidity = bme.read()
    return temperature

if library_type == 'inky':
    from inky.auto import auto
    from PIL import Image, ImageDraw, ImageFont

    inky = auto(ask_user=True, verbose=True)
    img = Image.new("RGB", (inky.width, inky.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = font_big

    temp = read_temp()
    temp_str = f"{temp:.1f}C"
    label = "Temperature"

    bbox = draw.textbbox((0, 0), temp_str, font=font_big)
    x = (inky.width - (bbox[2] - bbox[0])) // 2
    y = (inky.height - (bbox[3] - bbox[1])) // 2 - 10
    draw.text((x, y), temp_str, (0, 0, 0), font=font_big)

    bbox = draw.textbbox((0, 0), label, font=font_small)
    lx = (inky.width - (bbox[2] - bbox[0])) // 2
    draw.text((lx, y - 40), label, (100, 100, 100), font=font_small)

    inky.set_image(img)
    inky.show()

elif library_type == 'badgeware':
    from badgeware import run

    last_temp = [0.0]
    frame = [0]

    def update():
        if frame[0] % 60 == 0:
            last_temp[0] = read_temp()
        frame[0] += 1

        screen.pen = color.rgb(0, 0, 0)
        screen.clear()

        screen.pen = color.rgb(255, 255, 255)
        screen.font = rom_font.winds

        temp_str = f"{last_temp[0]:.1f}C"
        tw, th = screen.measure_text(temp_str)
        x = (screen.width - tw) // 2
        screen.text(temp_str, x, 10)

    run(update)

elif "presto" in device_name.lower():
    from presto import Presto
    import time

    presto = Presto()
    display = presto.display
    WIDTH, HEIGHT = display.get_bounds()

    WHITE = display.create_pen(255, 255, 255)
    BLACK = display.create_pen(0, 0, 0)
    GRAY = display.create_pen(150, 150, 150)

    while True:
        temp = read_temp()
        temp_str = f"{temp:.1f}C"

        display.set_pen(BLACK)
        display.clear()

        display.set_font("bitmap8")

        display.set_pen(WHITE)
        display.text(temp_str, 10, HEIGHT // 2 - 30, WIDTH, 6)

        display.set_pen(GRAY)
        display.text("Temperature", 10, HEIGHT // 2 + 40, WIDTH, 2)

        display.update()
        presto.update()
        time.sleep(1)

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
    GRAY = display.create_pen(150, 150, 150)

    while True:
        temp = read_temp()
        temp_str = f"{temp:.1f}C"

        display.set_pen(WHITE)
        display.clear()

        display.set_font("bitmap8")

        display.set_pen(BLACK)
        display.text(temp_str, 10, HEIGHT // 2 - 30, WIDTH, 5)

        display.set_pen(GRAY)
        display.text("Temperature", 10, HEIGHT // 2 + 30, WIDTH, 2)

        display.update()
        time.sleep(1)
