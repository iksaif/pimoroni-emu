"""TFT display renderer using pygame."""

import threading
from typing import List, Tuple
from emulator.display.base import BaseDisplay, draw_memory_bar
from emulator import get_state

# Lazy import pygame to allow headless operation
pygame = None

# Lazy import sensor panel
_sensor_panel_class = None


def _get_sensor_panel_class():
    global _sensor_panel_class
    if _sensor_panel_class is None:
        from emulator.hardware.sensor_panel import SensorPanel
        _sensor_panel_class = SensorPanel
    return _sensor_panel_class


def _init_pygame():
    global pygame
    if pygame is None:
        import pygame as pg
        pygame = pg


class TFTDisplay(BaseDisplay):
    """Renderer for TFT/IPS displays (Tufty, Presto)."""

    def __init__(self, device, headless: bool = False):
        super().__init__(device, headless)
        self._pygame_surface = None
        self._display_surface = None   # Back buffer: only app thread writes
        self._ready_surface = None     # Front buffer: only main thread reads
        self._dirty = False
        self._render_lock = threading.Lock()
        self._clock = None
        self._sensor_panel = None

    def init(self):
        """Initialize pygame window."""
        if self.headless:
            # In headless mode, we just use PIL
            return

        _init_pygame()

        # Initialize pygame
        pygame.init()

        # Create window
        win_size = self.device.get_window_size()
        self._window = pygame.display.set_mode(win_size)
        pygame.display.set_caption(f"Pimoroni Emulator - {self.device.name}")

        # Create surface for the display content (native resolution)
        self._display_surface = pygame.Surface(
            (self.device.display_width, self.device.display_height)
        )

        self._clock = pygame.time.Clock()

        # Create sensor panel on right side of window
        SensorPanel = _get_sensor_panel_class()
        panel_width = 120
        self._sensor_panel = SensorPanel(
            x=win_size[0] - panel_width - 5,
            y=35,
            width=panel_width
        )

        if get_state().get("trace"):
            print(f"[TFTDisplay] Initialized {win_size[0]}x{win_size[1]} window")

    def render(self, buffer: List[List[int]]):
        """Render framebuffer to back buffer (called from app thread).

        Does NOT touch the pygame window. The main thread picks up the
        new frame via tick().
        """
        self._last_buffer = buffer
        self._frame_count += 1

        if self.headless:
            self._autosave_frame()
            return

        if not self._display_surface:
            return

        _init_pygame()

        # Draw buffer to back surface (only app thread touches this)
        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        for y in range(min(height, self.device.display_height)):
            for x in range(min(width, self.device.display_width)):
                color = buffer[y][x]
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                self._display_surface.set_at((x, y), (r, g, b))

        # Publish completed frame to front buffer
        with self._render_lock:
            self._ready_surface = self._display_surface.copy()
            self._dirty = True

        # Autosave if enabled
        self._autosave_frame()

    def _draw_window(self):
        """Draw the full emulator window (must be called from main thread)."""
        if not self._window:
            return

        # Grab front buffer snapshot
        with self._render_lock:
            surface = self._ready_surface

        if not surface:
            return

        # Clear window
        self._window.fill((30, 30, 30))

        # Get display position
        disp_rect = self.device.get_display_rect()

        # Scale display surface using nearest-neighbor (pixel-perfect, no smoothing)
        # display_scale is always an integer, ensuring pixel-perfect rendering
        scaled = pygame.transform.scale(
            surface,
            (disp_rect[2], disp_rect[3])
        )

        # Draw display with border
        border_rect = (disp_rect[0] - 2, disp_rect[1] - 2,
                       disp_rect[2] + 4, disp_rect[3] + 4)
        pygame.draw.rect(self._window, (60, 60, 60), border_rect)
        self._window.blit(scaled, (disp_rect[0], disp_rect[1]))

        # Draw status bar
        self._draw_status_bar()

        # Draw RGB LEDs if device has them
        if self.device.num_rgb_leds > 0:
            self._draw_rgb_leds()

        # Draw button indicators
        self._draw_buttons()

        # Draw buzzer indicator
        self._draw_buzzer()

        # Draw sensor panel if sensors are active
        if self._sensor_panel:
            self._sensor_panel.update()
            if self._sensor_panel.has_sensors():
                self._sensor_panel.render(self._window)

        # Update display
        pygame.display.flip()

        # Cap frame rate
        if self._clock:
            self._clock.tick(60)

    def _draw_status_bar(self):
        """Draw status bar at top of window."""
        font = pygame.font.SysFont("monospace", 14)

        # Device name
        text = font.render(f"{self.device.name}", True, (200, 200, 200))
        self._window.blit(text, (10, 10))

        # Frame count
        text = font.render(f"Frame: {self._frame_count}", True, (150, 150, 150))
        win_w = self.device.get_window_size()[0]
        self._window.blit(text, (win_w - 120, 10))

        # Memory bar
        mem = self._get_memory_info()
        if mem:
            draw_memory_bar(pygame, self._window, 10, 28, 150, mem[0], mem[1])

    def _draw_rgb_leds(self):
        """Draw RGB LED indicators."""
        state = get_state()
        presto = state.get("presto")

        if not presto:
            return

        leds = presto.get_leds()
        disp_rect = self.device.get_display_rect()
        center_x = disp_rect[0] + disp_rect[2] // 2
        center_y = disp_rect[1] + disp_rect[3] // 2

        for i, (r, g, b) in enumerate(leds):
            if i < len(self.device.rgb_led_positions):
                dx, dy = self.device.rgb_led_positions[i]
                # LED positions are in base coordinates, scale them with display
                scale = self.device.display_scale
                x = center_x + dx * scale
                y = center_y + dy * scale

                # Draw LED glow
                if r > 0 or g > 0 or b > 0:
                    glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (r, g, b, 100), (15, 15), 15)
                    self._window.blit(glow_surf, (x - 15, y - 15))

                # Draw LED
                pygame.draw.circle(self._window, (r, g, b), (x, y), 8)
                pygame.draw.circle(self._window, (100, 100, 100), (x, y), 8, 1)

    def _draw_buttons(self):
        """Draw button state indicators."""
        state = get_state()
        buttons = state.get("buttons", {})

        if not self.device.buttons:
            return

        win_h = self.device.get_window_size()[1]
        font = pygame.font.SysFont("monospace", 12)

        x = 10
        for btn_config in self.device.buttons:
            # Check if button is pressed
            btn = buttons.get(btn_config.pin)
            pressed = btn._pressed if btn else False

            color = (100, 200, 100) if pressed else (80, 80, 80)
            pygame.draw.rect(self._window, color, (x, win_h - 30, 40, 20), border_radius=3)

            text = font.render(btn_config.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(x + 20, win_h - 20))
            self._window.blit(text, text_rect)

            x += 50

    def _draw_buzzer(self):
        """Draw buzzer frequency indicator if active."""
        state = get_state()
        buzzer = state.get("buzzer")
        if not buzzer or buzzer._freq <= 0:
            return

        font = pygame.font.SysFont("monospace", 12)
        win_w = self.device.get_window_size()[0]

        # Draw speaker icon and frequency
        freq = buzzer._freq
        note = f"{freq}Hz"
        color = (255, 200, 50)
        text = font.render(f"♪ {note}", True, color)
        self._window.blit(text, (win_w - 120, 28))

    def get_surface(self):
        """Get pygame surface or PIL Image."""
        if self.headless:
            if self._last_buffer:
                return self._buffer_to_image(self._last_buffer)
            return None
        with self._render_lock:
            return self._ready_surface

    def tick(self):
        """Redraw window if a new frame is ready (call from main thread)."""
        if self._dirty:
            self._dirty = False
            self._draw_window()

    def refresh_ui(self):
        """Redraw the window using the last rendered frame.

        Called by the main event loop to update UI elements (sensor panel,
        buttons) without waiting for the app to call render().
        """
        if not self.headless and self._ready_surface:
            self._draw_window()

    def get_button_at(self, x: int, y: int) -> str | None:
        """Return the key name of the button indicator at (x, y), or None."""
        if not self.device.buttons:
            return None
        win_h = self.device.get_window_size()[1]
        bx = 10
        for btn_config in self.device.buttons:
            if bx <= x < bx + 40 and win_h - 30 <= y < win_h - 10:
                return btn_config.key
            bx += 50
        return None

    def handle_mouse(self, x: int, y: int, pressed: bool) -> bool:
        """Handle mouse events. Returns True if event was consumed by UI."""
        if self._sensor_panel and self._sensor_panel.has_sensors():
            if self._sensor_panel.handle_mouse(x, y, pressed):
                self.refresh_ui()
                return True
        return False

    def close(self):
        """Close pygame window."""
        if not self.headless and pygame:
            pygame.quit()
