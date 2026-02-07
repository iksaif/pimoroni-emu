"""Universal Hello World app that works on all device types."""

# Check emulator state for device type
try:
    from emulator import get_state
    device = get_state().get("device")
    device_name = device.name if device else "Unknown"
    device_type = device.display_type if device else "unknown"
    library_type = getattr(device, 'library_type', 'picographics')
except ImportError:
    device_name = "Unknown"
    device_type = "unknown"
    library_type = "picographics"

if library_type == 'inky':
    # Raspberry Pi Inky device
    from inky.auto import auto
    from PIL import Image, ImageDraw, ImageFont

    inky = auto(ask_user=True, verbose=True)
    # Use RGB mode for proper color rendering
    img = Image.new("RGB", (inky.width, inky.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        font = ImageFont.load_default()

    text = f"Hello {device_name}!"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (inky.width - (bbox[2] - bbox[0])) // 2
    y = (inky.height - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, (0, 0, 0), font=font)

    inky.set_image(img)
    inky.show()

elif library_type == 'badgeware':
    # Blinky device (39x26 LED matrix)
    from badgeware import run

    def update():
        screen.pen = color.rgb(0, 0, 0)
        screen.clear()

        # Use a small font for the tiny display
        screen.pen = color.rgb(255, 255, 255)
        screen.font = rom_font.winds  # Small font

        # Center "Hello" on the display
        screen.text("Hello", 7, 10)

    run(update)

elif "presto" in device_name.lower():
    # Presto device with touch
    from presto import Presto
    presto = Presto()
    display = presto.display
    WIDTH, HEIGHT = display.get_bounds()
    display.set_pen(display.create_pen(0, 0, 0))
    display.clear()
    display.set_pen(display.create_pen(255, 255, 255))
    display.set_font("bitmap8")
    display.text("Hello Presto!", 10, HEIGHT // 2 - 20, WIDTH, 4)
    display.update()
    presto.update()

else:
    # Generic picographics device (Tufty, Badger, etc)
    from picographics import PicoGraphics

    # Get the appropriate display constant
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
    display.set_pen(WHITE)
    display.clear()
    display.set_pen(BLACK)
    display.set_font("bitmap8")
    display.text(f"Hello {device_name}!", 10, HEIGHT // 2 - 10, WIDTH, 3)
    display.update()

print(f"Hello app running on {device_name}!")

# Keep running (like a real badge app)
import time
while True:
    time.sleep(0.1)
