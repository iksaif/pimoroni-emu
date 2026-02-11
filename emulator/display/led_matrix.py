"""LED matrix display renderer for Blinky 2350."""

import copy
import threading
from typing import List, Optional
from emulator.display.base import BaseDisplay, draw_memory_bar
from emulator import get_state

# Lazy import pygame
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


class LEDMatrixDisplay(BaseDisplay):
    """Renderer for LED matrix displays (Blinky)."""

    def __init__(self, device, headless: bool = False):
        super().__init__(device, headless)
        self._pygame_surface = None
        self._ready_buffer = None   # Front buffer: only main thread reads
        self._dirty = False
        self._render_lock = threading.Lock()
        self._clock = None
        self._sensor_panel = None

        # LED rendering settings
        self._led_radius = 4
        self._led_spacing = 10
        self._glow_enabled = True

    def init(self):
        """Initialize pygame window."""
        if self.headless:
            return

        _init_pygame()
        pygame.init()

        # Calculate window size based on LED grid
        self._led_spacing = self.device.display_scale
        self._led_radius = max(2, self._led_spacing // 2 - 1)

        panel_width = 130
        win_width = (self.device.display_width * self._led_spacing +
                     self._led_spacing + 100 + panel_width)
        win_height = (self.device.display_height * self._led_spacing +
                      self._led_spacing + 80)

        self._window = pygame.display.set_mode((win_width, win_height))
        pygame.display.set_caption(f"Pimoroni Emulator - {self.device.name}")

        self._clock = pygame.time.Clock()

        # Create sensor panel on right side of window
        SensorPanel = _get_sensor_panel_class()
        self._sensor_panel = SensorPanel(
            x=win_width - panel_width - 5,
            y=35,
            width=panel_width - 5
        )

        if get_state().get("trace"):
            print(f"[LEDMatrixDisplay] Initialized {win_width}x{win_height} window")

    def render(self, buffer: List[List[int]]):
        """Render framebuffer as LED matrix (called from app thread).

        Does NOT touch the pygame window. The main thread picks up the
        new frame via tick().
        """
        self._last_buffer = buffer
        self._frame_count += 1

        if self.headless:
            self._autosave_frame()
            return

        if not self._window:
            return

        # Publish a snapshot to front buffer for the main thread
        with self._render_lock:
            self._ready_buffer = copy.deepcopy(buffer)
            self._dirty = True

        # Autosave if enabled
        self._autosave_frame()

    def _draw_window(self, buffer=None):
        """Draw the full emulator window (must be called from main thread)."""
        if not self._window:
            return

        if buffer is None:
            with self._render_lock:
                buffer = self._ready_buffer
        if buffer is None:
            return

        _init_pygame()

        # Clear window
        self._window.fill((20, 20, 25))

        # Draw status bar
        self._draw_status_bar()

        # Calculate LED grid position
        grid_x = 50
        grid_y = 40

        # Draw LED grid background
        grid_width = self.device.display_width * self._led_spacing + self._led_spacing
        grid_height = self.device.display_height * self._led_spacing + self._led_spacing
        pygame.draw.rect(
            self._window,
            (15, 15, 18),
            (grid_x - 5, grid_y - 5, grid_width + 10, grid_height + 10),
            border_radius=5
        )

        # Draw LEDs
        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        for y in range(min(height, self.device.display_height)):
            for x in range(min(width, self.device.display_width)):
                led_x = grid_x + x * self._led_spacing + self._led_spacing // 2
                led_y = grid_y + y * self._led_spacing + self._led_spacing // 2

                # Get brightness (for LED matrix, color value is brightness)
                color = buffer[y][x]
                if self.device.is_color:
                    # Color display - use actual RGB
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                else:
                    # Monochrome - use brightness value
                    brightness = color & 0xFF
                    r = g = b = brightness

                # Draw glow effect for bright LEDs
                if self._glow_enabled and (r > 50 or g > 50 or b > 50):
                    glow_radius = self._led_radius + 2
                    glow_alpha = min(150, (r + g + b) // 3)
                    glow_surf = pygame.Surface(
                        (glow_radius * 4, glow_radius * 4),
                        pygame.SRCALPHA
                    )
                    pygame.draw.circle(
                        glow_surf,
                        (r, g, b, glow_alpha),
                        (glow_radius * 2, glow_radius * 2),
                        glow_radius * 2
                    )
                    self._window.blit(
                        glow_surf,
                        (led_x - glow_radius * 2, led_y - glow_radius * 2)
                    )

                # Draw LED
                pygame.draw.circle(
                    self._window,
                    (r, g, b),
                    (led_x, led_y),
                    self._led_radius
                )

                # Draw LED outline (dim)
                pygame.draw.circle(
                    self._window,
                    (40, 40, 45),
                    (led_x, led_y),
                    self._led_radius,
                    1
                )

        # Draw button indicators
        self._draw_buttons()

        # Draw QwSTPad gamepad widget if registered
        self._draw_qwstpad()

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
        """Draw status bar."""
        font = pygame.font.SysFont("monospace", 14)

        # Device name
        text = font.render(f"{self.device.name}", True, (200, 200, 200))
        self._window.blit(text, (10, 10))

        # Frame count
        text = font.render(f"Frame: {self._frame_count}", True, (150, 150, 150))
        win_w = self._window.get_width()
        self._window.blit(text, (win_w - 120, 10))

        # Memory bar
        mem = self._get_memory_info()
        if mem:
            draw_memory_bar(pygame, self._window, 10, 28, 150, mem[0], mem[1])

    def _draw_buttons(self):
        """Draw button state indicators."""
        state = get_state()
        buttons = state.get("buttons", {})

        if not self.device.buttons:
            return

        win_h = self._window.get_height()
        font = pygame.font.SysFont("monospace", 12)

        x = 10
        for btn_config in self.device.buttons:
            btn = buttons.get(btn_config.pin)
            pressed = btn._pressed if btn else False

            color = (100, 200, 100) if pressed else (60, 60, 65)
            pygame.draw.rect(
                self._window,
                color,
                (x, win_h - 30, 40, 20),
                border_radius=3
            )

            text = font.render(btn_config.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(x + 20, win_h - 20))
            self._window.blit(text, text_rect)

            x += 50

    def tick(self):
        """Redraw window if a new frame is ready (call from main thread)."""
        if self._dirty:
            self._dirty = False
            self._draw_window()

    def refresh_ui(self):
        """Redraw the window using the last rendered frame."""
        if not self.headless and self._window and self._ready_buffer:
            self._draw_window()

    def get_button_at(self, x: int, y: int) -> str | None:
        """Return the key name of the button indicator at (x, y), or None."""
        if not self.device.buttons or not self._window:
            return None
        win_h = self._window.get_height()
        bx = 10
        for btn_config in self.device.buttons:
            if bx <= x < bx + 40 and win_h - 30 <= y < win_h - 10:
                return btn_config.key
            bx += 50
        return None

    def _get_qwstpad_layout(self):
        """Compute QwSTPad widget button positions."""
        state = get_state()
        if "qwstpad" not in state:
            return None

        win_w = self._window.get_width()
        win_h = self._window.get_height()

        btn_size = 28
        gap = 4
        # Position below the LED grid + device buttons
        grid_bottom = (40 + self.device.display_height * self._led_spacing +
                       self._led_spacing + 10)
        base_y = max(grid_bottom + 35, win_h - btn_size * 3 - gap * 2 - 20)
        center_x = 50 + (self.device.display_width * self._led_spacing) // 2

        buttons = []
        # D-pad
        dpad_cx = center_x - 80
        dpad_cy = base_y + btn_size + gap
        buttons.append(("up",    (dpad_cx, dpad_cy - btn_size - gap, btn_size, btn_size), "U"))
        buttons.append(("down",  (dpad_cx, dpad_cy + btn_size + gap, btn_size, btn_size), "D"))
        buttons.append(("left",  (dpad_cx - btn_size - gap, dpad_cy, btn_size, btn_size), "L"))
        buttons.append(("right", (dpad_cx + btn_size + gap, dpad_cy, btn_size, btn_size), "R"))

        # Face buttons (diamond)
        face_cx = center_x + 80
        face_cy = dpad_cy
        buttons.append(("z", (face_cx, face_cy + btn_size + gap, btn_size, btn_size), "A"))
        buttons.append(("x", (face_cx + btn_size + gap, face_cy, btn_size, btn_size), "B"))
        buttons.append(("c", (face_cx, face_cy - btn_size - gap, btn_size, btn_size), "X"))
        buttons.append(("v", (face_cx - btn_size - gap, face_cy, btn_size, btn_size), "Y"))

        # +/- buttons
        buttons.append(("=", (center_x + 10, dpad_cy - 5, btn_size, btn_size // 2 + 4), "+"))
        buttons.append(("-", (center_x - 10 - btn_size, dpad_cy - 5, btn_size, btn_size // 2 + 4), "-"))

        return buttons

    def _draw_qwstpad(self):
        """Draw QwSTPad gamepad widget if registered."""
        layout = self._get_qwstpad_layout()
        if not layout:
            return

        # Resize window if needed
        last_btn_bottom = max(r[1] + r[3] for _, r, _ in layout) + 10
        win_w, win_h = self._window.get_size()
        if last_btn_bottom > win_h and not getattr(self, '_qwstpad_resized', False):
            self._qwstpad_resized = True
            self._window = pygame.display.set_mode((win_w, last_btn_bottom + 10))
            return

        state = get_state()
        bitmask = state.get("qwstpad_buttons", 0)
        qwstpad = state.get("qwstpad")

        from emulator.mocks.qwstpad import KEY_TO_BUTTON

        font = pygame.font.SysFont("monospace", 13, bold=True)

        for key_name, rect, label in layout:
            x, y, w, h = rect
            mask = KEY_TO_BUTTON.get(key_name, 0)
            pressed = bool(bitmask & mask)

            if pressed:
                bg_color = (80, 200, 80)
                text_color = (0, 0, 0)
            else:
                bg_color = (60, 60, 65)
                text_color = (200, 200, 200)

            pygame.draw.rect(self._window, bg_color, (x, y, w, h), border_radius=4)
            pygame.draw.rect(self._window, (90, 90, 95), (x, y, w, h), 1, border_radius=4)

            text = font.render(label, True, text_color)
            text_rect = text.get_rect(center=(x + w // 2, y + h // 2))
            self._window.blit(text, text_rect)

        # LED indicators
        if qwstpad:
            led_states = qwstpad._led_states
            led_y = layout[0][1][1] - 20
            center_x = 50 + (self.device.display_width * self._led_spacing) // 2
            led_start_x = center_x - 30
            for i in range(4):
                lx = led_start_x + i * 16
                lit = bool(led_states & (1 << i))
                color = (0, 255, 100) if lit else (35, 35, 40)
                pygame.draw.circle(self._window, color, (lx + 4, led_y + 4), 5)
                pygame.draw.circle(self._window, (70, 70, 75), (lx + 4, led_y + 4), 5, 1)

    def get_qwstpad_button_at(self, x: int, y: int) -> str | None:
        """Return the key name of the QwSTPad button at (x, y), or None."""
        layout = self._get_qwstpad_layout()
        if not layout:
            return None
        for key_name, rect, _label in layout:
            bx, by, bw, bh = rect
            if bx <= x < bx + bw and by <= y < by + bh:
                return key_name
        return None

    def handle_mouse(self, x: int, y: int, pressed: bool) -> bool:
        """Handle mouse events. Returns True if event was consumed by UI."""
        if self._sensor_panel and self._sensor_panel.has_sensors():
            if self._sensor_panel.handle_mouse(x, y, pressed):
                self.refresh_ui()
                return True
        return False

    def get_surface(self):
        """Get pygame surface or PIL Image."""
        if self.headless:
            if self._last_buffer:
                return self._buffer_to_image(self._last_buffer)
            return None
        return self._window

    def close(self):
        """Close pygame window."""
        if not self.headless and pygame:
            pygame.quit()

    def set_glow(self, enabled: bool):
        """Enable or disable LED glow effect."""
        self._glow_enabled = enabled
