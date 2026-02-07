"""Simple demo for Inky Impression (Raspberry Pi/inky library)."""

from PIL import Image, ImageDraw, ImageFont
from inky.auto import auto

# Auto-detect and initialize the display
inky_display = auto(verbose=True)

# Get display dimensions
WIDTH = inky_display.WIDTH
HEIGHT = inky_display.HEIGHT

# Create a new image with white background
img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Define 7-color palette (ACeP)
COLORS = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (0, 128, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 0, 0),      # Red
    (255, 255, 0),    # Yellow
    (255, 128, 0),    # Orange
]
COLOR_NAMES = ["Black", "White", "Green", "Blue", "Red", "Yellow", "Orange"]

# Draw color swatches
swatch_w = WIDTH // 7
swatch_h = 80
y = 20

for i, (color, name) in enumerate(zip(COLORS, COLOR_NAMES)):
    x = i * swatch_w
    draw.rectangle([x + 5, y, x + swatch_w - 5, y + swatch_h], fill=color)

    # Label in contrasting color
    text_color = (255, 255, 255) if i in [0, 2, 3] else (0, 0, 0)
    draw.text((x + 10, y + swatch_h + 10), name, fill=text_color)

# Draw title and info
draw.text((20, HEIGHT // 2 - 60), "Inky Impression Demo", fill=(0, 0, 0))
draw.text((20, HEIGHT // 2 - 20), "7-Color ACeP E-Ink Display", fill=(0, 0, 0))
draw.text((20, HEIGHT // 2 + 20), f"Resolution: {WIDTH}x{HEIGHT}", fill=(0, 0, 0))
draw.text((20, HEIGHT // 2 + 60), "Raspberry Pi HAT with inky library", fill=(0, 0, 128))

# Draw some colorful shapes
# Red circle
draw.ellipse([WIDTH - 200, HEIGHT - 150, WIDTH - 100, HEIGHT - 50], fill=(255, 0, 0))

# Green rectangle
draw.rectangle([WIDTH - 350, HEIGHT - 150, WIDTH - 250, HEIGHT - 50], fill=(0, 128, 0))

# Blue triangle
draw.polygon([(WIDTH - 500, HEIGHT - 50), (WIDTH - 450, HEIGHT - 150), (WIDTH - 400, HEIGHT - 50)],
             fill=(0, 0, 255))

# Yellow star points
draw.polygon([
    (100, HEIGHT - 100), (120, HEIGHT - 140), (140, HEIGHT - 100),
    (180, HEIGHT - 100), (150, HEIGHT - 70),
    (160, HEIGHT - 30), (120, HEIGHT - 60),
    (80, HEIGHT - 30), (90, HEIGHT - 70),
    (60, HEIGHT - 100),
], fill=(255, 255, 0))

# Display the image
print(f"Displaying on {WIDTH}x{HEIGHT} Inky Impression...")
inky_display.set_image(img)
inky_display.show()

print("Done! Display should update in ~30 seconds.")
