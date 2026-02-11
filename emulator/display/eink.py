"""E-ink display renderer for Badger 2350 and Inky Frame."""

from typing import List, Optional, Tuple
import time as _time
from emulator.display.base import BaseDisplay, draw_memory_bar
from emulator import get_state

# Lazy import pygame
pygame = None


def _init_pygame():
    global pygame
    if pygame is None:
        import pygame as pg
        pygame = pg


# Color e-ink palettes
# Spectra 6 colors (Inky Frame 7.3")
SPECTRA_6_PALETTE = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (0, 128, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 0, 0),      # Red
    (255, 255, 0),    # Yellow
]

# ACeP 7 colors (Inky Frame 4.0", 5.8")
ACEP_7_PALETTE = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (0, 128, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 0, 0),      # Red
    (255, 255, 0),    # Yellow
    (255, 128, 0),    # Orange
]


def _find_nearest_color(r: int, g: int, b: int, palette: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Find the nearest color in the palette using Euclidean distance."""
    best_color = palette[0]
    best_dist = float('inf')

    for pr, pg, pb in palette:
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_color = (pr, pg, pb)

    return best_color


class EInkDisplay(BaseDisplay):
    """Renderer for e-ink displays (Badger 2350, Inky Frame)."""

    def __init__(self, device, headless: bool = False):
        super().__init__(device, headless)
        self._pygame_surface = None
        self._display_surface = None
        self._clock = None

        # E-ink simulation
        self._refresh_animation = False
        self._refresh_start_time = 0
        self._refresh_duration = 1.5  # seconds for visual refresh animation
        self._prev_display_surface = None  # previous frame for transition

        # E-ink dithering pattern
        self._dither = True

        # Color e-ink support
        self._is_color = getattr(device, 'is_color', False)
        self._eink_colors = getattr(device, 'eink_colors', 2)

        # Select palette based on device
        if self._eink_colors == 6:
            self._palette = SPECTRA_6_PALETTE
        elif self._eink_colors == 7:
            self._palette = ACEP_7_PALETTE
        else:
            self._palette = [(0, 0, 0), (255, 255, 255)]  # B&W

    def init(self):
        """Initialize pygame window."""
        if self.headless:
            return

        _init_pygame()
        pygame.init()

        # Create window
        win_size = self.device.get_window_size()
        self._window = pygame.display.set_mode(win_size)
        pygame.display.set_caption(f"Pimoroni Emulator - {self.device.name}")

        # Create surface for e-ink display
        self._display_surface = pygame.Surface(
            (self.device.display_width, self.device.display_height)
        )

        self._clock = pygame.time.Clock()

        if get_state().get("trace"):
            print(f"[EInkDisplay] Initialized {win_size[0]}x{win_size[1]} window")

    def _convert_buffer(self, buffer: List[List[int]]):
        """Convert framebuffer to e-ink colors on _display_surface."""
        _init_pygame()

        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        for y in range(min(height, self.device.display_height)):
            for x in range(min(width, self.device.display_width)):
                color = buffer[y][x]

                # Check if this is an RGB packed value (from create_pen) or a pen index
                if color > 255:
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                else:
                    # Pen index (0-15 for e-ink grayscale)
                    r = g = b = int(color * 255 / 15) if color <= 15 else color

                if self._is_color:
                    pixel_color = _find_nearest_color(r, g, b, self._palette)
                    pixel_color = (
                        min(255, pixel_color[0] - 10 if pixel_color[0] > 10 else pixel_color[0]),
                        min(255, pixel_color[1] - 10 if pixel_color[1] > 10 else pixel_color[1]),
                        min(255, pixel_color[2] - 5 if pixel_color[2] > 5 else pixel_color[2])
                    )
                else:
                    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                    if self._dither:
                        threshold = 128 + ((x % 2) * 32 - 16) + ((y % 2) * 32 - 16)
                        if gray > threshold:
                            pixel_color = (245, 245, 240)
                        else:
                            pixel_color = (30, 30, 35)
                    else:
                        if gray > 128:
                            pixel_color = (245, 245, 240)
                        else:
                            pixel_color = (30, 30, 35)

                self._display_surface.set_at((x, y), pixel_color)

    def render(self, buffer: List[List[int]]):
        """Render framebuffer as e-ink display with slow refresh animation."""
        self._last_buffer = buffer
        self._frame_count += 1

        if self.headless:
            if self._display_surface:
                self._convert_buffer(buffer)
            self._autosave_frame()
            return

        if not self._display_surface:
            return

        # Save previous frame for transition
        self._prev_display_surface = self._display_surface.copy()

        # Convert new buffer to e-ink colors
        self._convert_buffer(buffer)
        new_surface = self._display_surface.copy()

        # Animate the refresh: invert flash -> black -> progressive reveal
        self._refresh_animation = True
        self._refresh_start_time = _time.time()
        disp_h = self.device.display_height

        phase_invert = 0.15   # brief invert
        phase_black = 0.15    # brief black
        phase_reveal = self._refresh_duration - phase_invert - phase_black

        while True:
            elapsed = _time.time() - self._refresh_start_time
            if elapsed >= self._refresh_duration:
                break

            if elapsed < phase_invert:
                # Phase 1: invert the old image
                inverted = self._prev_display_surface.copy()
                inverted.fill((255, 255, 255))
                inverted.blit(self._prev_display_surface, (0, 0),
                              special_flags=pygame.BLEND_RGB_SUB)
                self._display_surface = inverted
            elif elapsed < phase_invert + phase_black:
                # Phase 2: black flash
                self._display_surface.fill((30, 30, 35))
            else:
                # Phase 3: progressive top-to-bottom reveal
                reveal_t = (elapsed - phase_invert - phase_black) / phase_reveal
                reveal_row = int(reveal_t * disp_h)

                # Start from blank (e-ink white) and reveal new content top-down
                self._display_surface.fill((245, 245, 240))
                self._display_surface.blit(
                    new_surface,
                    (0, 0),
                    (0, 0, self.device.display_width, reveal_row),
                )

            self._draw_window()
            _time.sleep(0.016)  # ~60 fps animation

        # Final: show complete new image
        self._display_surface = new_surface
        self._refresh_animation = False
        self._draw_window()

        # Autosave if enabled
        self._autosave_frame()

    def _draw_window(self):
        """Draw the full emulator window."""
        if not self._window:
            return

        # E-ink paper background
        self._window.fill((200, 195, 185))

        # Get display position
        disp_rect = self.device.get_display_rect()

        # Scale display surface
        scaled = pygame.transform.scale(
            self._display_surface,
            (disp_rect[2], disp_rect[3])
        )

        # Draw display bezel
        bezel_color = (60, 60, 65)
        bezel_rect = (disp_rect[0] - 8, disp_rect[1] - 8,
                      disp_rect[2] + 16, disp_rect[3] + 16)
        pygame.draw.rect(self._window, bezel_color, bezel_rect, border_radius=4)

        # Draw display
        self._window.blit(scaled, (disp_rect[0], disp_rect[1]))

        # Draw status bar
        self._draw_status_bar()

        # Draw buttons
        self._draw_buttons()

        # Update display
        pygame.display.flip()

        # Cap frame rate
        if self._clock:
            self._clock.tick(60)

    def _draw_status_bar(self):
        """Draw status bar."""
        font = pygame.font.SysFont("monospace", 14)

        # Device name
        text = font.render(f"{self.device.name}", True, (60, 60, 60))
        self._window.blit(text, (10, 10))

        # Refresh indicator
        if self._refresh_animation:
            text = font.render("REFRESHING", True, (200, 100, 100))
        else:
            text = font.render(f"Frame: {self._frame_count}", True, (100, 100, 100))
        win_w = self.device.get_window_size()[0]
        self._window.blit(text, (win_w - 120, 10))

        # Memory bar
        mem = self._get_memory_info()
        if mem:
            draw_memory_bar(pygame, self._window, 10, 28, 150, mem[0], mem[1])

    def _draw_buttons(self):
        """Draw button indicators with LED dots."""
        state = get_state()
        buttons = state.get("buttons", {})
        leds = state.get("leds", {})

        if not self.device.buttons:
            return

        font = pygame.font.SysFont("monospace", 12)
        has_button_leds = getattr(self.device, 'has_button_leds', False)

        if has_button_leds:
            # Inky Frame layout: buttons vertically along the left edge
            disp_rect = self.device.get_display_rect()
            btn_x = disp_rect[0] - 38  # left of the display bezel
            disp_top = disp_rect[1]
            disp_h = disp_rect[3]
            n = len(self.device.buttons)
            spacing = disp_h / (n + 1)

            for i, btn_config in enumerate(self.device.buttons):
                btn = buttons.get(btn_config.pin)
                pressed = btn._pressed if btn else False
                btn_y = int(disp_top + spacing * (i + 1))

                # Button
                color = (80, 150, 80) if pressed else (100, 100, 100)
                pygame.draw.rect(
                    self._window, color,
                    (btn_x, btn_y - 10, 24, 20),
                    border_radius=3,
                )
                text = font.render(btn_config.name, True, (255, 255, 255))
                text_rect = text.get_rect(center=(btn_x + 12, btn_y))
                self._window.blit(text, text_rect)

                # LED dot to the left of button
                led_key = f"button_{btn_config.name.lower()}_led"
                led = leds.get(led_key)
                led_on = led and led.is_on if led else False
                led_color = (255, 255, 200) if led_on else (60, 60, 55)
                pygame.draw.circle(self._window, led_color, (btn_x - 8, btn_y), 4)
        else:
            # Badger / generic layout: buttons horizontally at the bottom
            win_h = self.device.get_window_size()[1]
            x = 10
            for btn_config in self.device.buttons:
                btn = buttons.get(btn_config.pin)
                pressed = btn._pressed if btn else False

                color = (80, 150, 80) if pressed else (100, 100, 100)
                pygame.draw.rect(
                    self._window, color,
                    (x, win_h - 30, 40, 20),
                    border_radius=3,
                )
                text = font.render(btn_config.name, True, (255, 255, 255))
                text_rect = text.get_rect(center=(x + 20, win_h - 20))
                self._window.blit(text, text_rect)
                x += 50

        # Draw busy/activity LED
        if getattr(self.device, 'has_busy_led', False):
            busy_led = leds.get("busy")
            busy_on = busy_led and busy_led.is_on if busy_led else False
            busy_color = (255, 180, 50) if busy_on else (60, 60, 55)
            win_w = self.device.get_window_size()[0]
            win_h = self.device.get_window_size()[1]
            pygame.draw.circle(self._window, busy_color, (win_w - 20, win_h - 20), 6)
            font_sm = pygame.font.SysFont("monospace", 10)
            label = font_sm.render("BUSY", True, (120, 120, 120))
            self._window.blit(label, (win_w - 42, win_h - 34))

    def refresh_ui(self):
        """Redraw window to update UI elements (buttons) without a new render."""
        if not self.headless and self._display_surface:
            self._draw_window()

    def get_button_at(self, x: int, y: int) -> str | None:
        """Return the key name of the button at window coords (x, y), or None."""
        if not self.device.buttons:
            return None

        has_button_leds = getattr(self.device, 'has_button_leds', False)

        if has_button_leds:
            # Inky Frame: vertical buttons along the left edge
            disp_rect = self.device.get_display_rect()
            btn_x = disp_rect[0] - 38
            disp_top = disp_rect[1]
            disp_h = disp_rect[3]
            n = len(self.device.buttons)
            spacing = disp_h / (n + 1)

            for i, btn_config in enumerate(self.device.buttons):
                btn_y = int(disp_top + spacing * (i + 1))
                if btn_x <= x < btn_x + 24 and btn_y - 10 <= y < btn_y + 10:
                    return btn_config.key
        else:
            # Badger: horizontal buttons at the bottom
            win_h = self.device.get_window_size()[1]
            bx = 10
            for btn_config in self.device.buttons:
                if bx <= x < bx + 40 and win_h - 30 <= y < win_h - 10:
                    return btn_config.key
                bx += 50

        return None

    def get_surface(self):
        """Get pygame surface or PIL Image."""
        if self.headless:
            if self._last_buffer:
                return self._buffer_to_image(self._last_buffer)
            return None
        return self._display_surface

    def close(self):
        """Close pygame window."""
        if not self.headless and pygame:
            pygame.quit()

    def set_dither(self, enabled: bool):
        """Enable or disable dithering."""
        self._dither = enabled

    def set_refresh_speed(self, duration: float):
        """Set refresh animation duration in seconds."""
        self._refresh_duration = max(0.1, min(2.0, duration))

    def _buffer_to_image(self, buffer):
        """Convert e-ink framebuffer to PIL Image.

        E-ink displays use pen values 0-15 for grayscale, not RGB packed values.
        This overrides the base class method to properly convert these values.
        """
        from PIL import Image

        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        img = Image.new("RGB", (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                color = buffer[y][x]

                # Check if this is an RGB packed value (from create_pen) or a pen index
                if color > 255:
                    # RGB packed value - extract components
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                else:
                    # Pen index (0-15 for e-ink grayscale)
                    # Convert to grayscale: 0=black, 15=white
                    r = g = b = int(color * 255 / 15) if color <= 15 else color

                if self._is_color:
                    # Color e-ink: find nearest palette color
                    pixel_color = _find_nearest_color(r, g, b, self._palette)
                    # Apply e-ink "paper" warmth
                    pixel_color = (
                        max(0, pixel_color[0] - 10),
                        max(0, pixel_color[1] - 10),
                        max(0, pixel_color[2] - 5)
                    )
                else:
                    # B&W e-ink: convert to grayscale and threshold
                    gray = int(0.299 * r + 0.587 * g + 0.114 * b)

                    # E-ink is typically black on white
                    # Threshold to black or white (with optional dithering)
                    if self._dither:
                        # Simple ordered dithering
                        threshold = 128 + ((x % 2) * 32 - 16) + ((y % 2) * 32 - 16)
                        if gray > threshold:
                            pixel_color = (245, 245, 240)  # E-ink white (slightly warm)
                        else:
                            pixel_color = (30, 30, 35)  # E-ink black
                    else:
                        if gray > 128:
                            pixel_color = (245, 245, 240)
                        else:
                            pixel_color = (30, 30, 35)

                pixels[x, y] = pixel_color

        return img
