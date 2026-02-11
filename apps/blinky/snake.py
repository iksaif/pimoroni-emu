"""Snake game for Blinky 2350 LED matrix."""

from picographics import PicoGraphics, DISPLAY_BLINKY
from pimoroni import Button
import time
import random

# Set up display
display = PicoGraphics(display=DISPLAY_BLINKY)
WIDTH, HEIGHT = display.get_bounds()

# Set up buttons
button_a = Button(7)   # Left
button_b = Button(8)   # Right
button_c = Button(9)   # Restart
button_up = Button(22)
button_down = Button(6)

# Colors (brightness levels for white LED matrix)
BLACK = display.create_pen(0, 0, 0)
DIM = display.create_pen(40, 40, 40)
BODY = display.create_pen(150, 150, 150)
HEAD = display.create_pen(255, 255, 255)
FOOD_COLOR = display.create_pen(255, 255, 255)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Game state
snake = []
direction = RIGHT
food = (0, 0)
score = 0
game_over = False
base_delay = 0.20  # seconds per move


def reset_game():
    global snake, direction, food, score, game_over, base_delay
    # Start snake in the center, 3 segments long
    cx, cy = WIDTH // 2, HEIGHT // 2
    snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
    direction = RIGHT
    score = 0
    game_over = False
    base_delay = 0.20
    place_food()


def place_food():
    global food
    while True:
        fx = random.randint(0, WIDTH - 1)
        fy = random.randint(0, HEIGHT - 1)
        if (fx, fy) not in snake:
            food = (fx, fy)
            return


def step():
    """Advance snake by one step. Returns False if game over."""
    global game_over, score, base_delay

    hx, hy = snake[0]
    dx, dy = direction
    nx, ny = hx + dx, hy + dy

    # Wall collision
    if nx < 0 or nx >= WIDTH or ny < 0 or ny >= HEIGHT:
        game_over = True
        return False

    # Self collision
    if (nx, ny) in snake:
        game_over = True
        return False

    # Move
    snake.insert(0, (nx, ny))

    # Check food
    if (nx, ny) == food:
        score += 1
        # Speed up slightly
        base_delay = max(0.06, base_delay - 0.005)
        place_food()
    else:
        snake.pop()

    return True


def draw_game():
    """Draw the current game state."""
    display.set_pen(BLACK)
    display.clear()

    # Draw food with pulsing brightness
    pulse = int(128 + 127 * ((time.ticks_ms() % 600) / 600.0 * 2 - 1) ** 2)
    food_pen = display.create_pen(pulse, pulse, pulse)
    display.set_pen(food_pen)
    display.pixel(food[0], food[1])

    # Draw snake body
    for i, (sx, sy) in enumerate(snake):
        if i == 0:
            display.set_pen(HEAD)
        else:
            display.set_pen(BODY)
        display.pixel(sx, sy)

    display.update()


def draw_game_over():
    """Flash screen and show score."""
    # Flash
    for _ in range(3):
        display.set_pen(display.create_pen(255, 255, 255))
        display.clear()
        display.update()
        time.sleep(0.1)
        display.set_pen(BLACK)
        display.clear()
        display.update()
        time.sleep(0.1)

    # Show score as scrolling text
    display.set_font("bitmap8")
    text = f"Score:{score}"
    text_w = display.measure_text(text, scale=1)
    scroll_x = WIDTH

    start = time.ticks_ms()
    while time.ticks_ms() - start < 3000:
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(HEAD)
        display.text(text, int(scroll_x), HEIGHT // 2 - 4, scale=1)
        scroll_x -= 1
        if scroll_x < -text_w:
            scroll_x = WIDTH
        display.update()

        if button_c.is_pressed():
            return
        time.sleep(0.04)


# Start
reset_game()
last_move = time.ticks_ms()

while True:
    # Read input
    if button_up.is_pressed() and direction != DOWN:
        direction = UP
    elif button_down.is_pressed() and direction != UP:
        direction = DOWN
    elif button_a.is_pressed() and direction != RIGHT:
        direction = LEFT
    elif button_b.is_pressed() and direction != LEFT:
        direction = RIGHT

    now = time.ticks_ms()
    if now - last_move >= base_delay * 1000:
        last_move = now
        if not game_over:
            step()

    if game_over:
        draw_game_over()
        reset_game()
        last_move = time.ticks_ms()
    else:
        draw_game()

    time.sleep(0.02)
