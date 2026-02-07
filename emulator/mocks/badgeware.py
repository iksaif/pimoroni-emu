"""Mock implementation of the badgeware module for Blinky 2350.

Badgeware provides the high-level API for the Blinky badge including
drawing primitives, shapes, colors, input handling, and more.
"""

import math
import time as _time
import builtins
from emulator import get_state


# --- Color ---

class _Color:
    """Color utilities for creating RGBA colors."""

    @staticmethod
    def rgb(r, g=None, b=None, a=255):
        """Create an RGBA color."""
        if g is None and b is None:
            # Single grayscale value
            return (r << 24) | (r << 16) | (r << 8) | 255
        return (int(r) << 24) | (int(g) << 16) | (int(b) << 8) | int(a)

    @staticmethod
    def hsv(h, s, v, a=255):
        """Create color from HSV values."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return _Color.rgb(int(r * 255), int(g * 255), int(b * 255), a)

    @property
    def black(self):
        return self.rgb(0, 0, 0)

    @property
    def white(self):
        return self.rgb(255, 255, 255)

    @property
    def red(self):
        return self.rgb(255, 0, 0)

    @property
    def green(self):
        return self.rgb(0, 255, 0)

    @property
    def blue(self):
        return self.rgb(0, 0, 255)

    @property
    def yellow(self):
        return self.rgb(255, 255, 0)

    @property
    def cyan(self):
        return self.rgb(0, 255, 255)

    @property
    def magenta(self):
        return self.rgb(255, 0, 255)


color = _Color()


# --- Rect ---

class rect:
    """Rectangle class."""

    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return f"rect({self.x}, {self.y}, {self.w}, {self.h})"


# --- Vec2 ---

class vec2:
    """2D vector class."""

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __add__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x + other.x, self.y + other.y)
        return vec2(self.x + other, self.y + other)

    def __sub__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x - other.x, self.y - other.y)
        return vec2(self.x - other, self.y - other)

    def __mul__(self, scalar):
        return vec2(self.x * scalar, self.y * scalar)

    def __repr__(self):
        return f"vec2({self.x}, {self.y})"

    def __iter__(self):
        yield self.x
        yield self.y


# --- Shape ---

class _Shape:
    """Shape factory for creating drawable shapes."""

    @staticmethod
    def rectangle(x, y, w, h):
        """Create a rectangle shape."""
        return ("rectangle", x, y, w, h)

    @staticmethod
    def circle(x, y, r):
        """Create a circle shape."""
        return ("circle", x, y, r)

    @staticmethod
    def line(x1, y1, x2, y2, thickness=1):
        """Create a line shape."""
        return ("line", x1, y1, x2, y2, thickness)

    @staticmethod
    def polygon(*points):
        """Create a polygon from points."""
        return ("polygon", points)


shape = _Shape()


# --- Brush ---

class _Brush:
    """Brush utilities for patterns and gradients."""

    @staticmethod
    def solid(color_val):
        """Create a solid color brush."""
        return ("solid", color_val)

    @staticmethod
    def pattern(fg, bg, pattern):
        """Create a pattern brush."""
        return ("pattern", fg, bg, pattern)

    @staticmethod
    def gradient(start, end, direction=0):
        """Create a gradient brush."""
        return ("gradient", start, end, direction)


brush = _Brush()


# --- IO (Input/Output) ---

class _IO:
    """Input/output handling for buttons and timing."""

    # Button constants
    BUTTON_A = 1
    BUTTON_B = 2
    BUTTON_C = 4
    BUTTON_UP = 8
    BUTTON_DOWN = 16
    BUTTON_HOME = 32

    def __init__(self):
        self._ticks_start = _time.time() * 1000
        self._pressed = 0
        self._released = 0

    @property
    def ticks(self):
        """Get milliseconds since start."""
        return int((_time.time() * 1000) - self._ticks_start)

    @property
    def pressed(self):
        """Get pressed button mask."""
        state = get_state()
        buttons = state.get("buttons", {})
        mask = 0
        # Map pin numbers to button constants
        pin_to_button = {
            7: self.BUTTON_A,
            8: self.BUTTON_B,
            9: self.BUTTON_C,
            22: self.BUTTON_UP,
            6: self.BUTTON_DOWN,
        }
        for pin, btn in buttons.items():
            if hasattr(btn, '_pressed') and btn._pressed:
                if pin in pin_to_button:
                    mask |= pin_to_button[pin]
        return mask

    @property
    def released(self):
        """Get released button mask."""
        return self._released

    def poll(self):
        """Poll button states."""
        # In emulator, button state is updated by the event loop
        pass


io = _IO()


# --- Image ---

class image:
    """Image/canvas class for drawing."""

    def __init__(self, width, height, buffer=None):
        self.width = width
        self.height = height
        self._buffer = buffer or bytearray(width * height)
        self._pen = color.white
        self._font = None
        self._clip = rect(0, 0, width, height)
        self._alpha = 255

    @staticmethod
    def load(filename):
        """Load an image from file."""
        # For emulator, create a placeholder image
        if get_state().get("trace"):
            print(f"[image] Loading {filename}")
        # Return a small placeholder
        return image(16, 16)

    @property
    def pen(self):
        return self._pen

    @pen.setter
    def pen(self, value):
        self._pen = value

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value

    @property
    def clip(self):
        return self._clip

    @clip.setter
    def clip(self, value):
        self._clip = value

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value

    def clear(self):
        """Clear the image with current pen color."""
        gray = self._color_to_gray(self._pen)
        for i in range(len(self._buffer)):
            self._buffer[i] = gray

    def pixel(self, x, y):
        """Draw a pixel at (x, y) with current pen."""
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            gray = self._color_to_gray(self._pen)
            self._buffer[y * self.width + x] = gray

    def shape(self, shape_def):
        """Draw a shape."""
        if not shape_def:
            return

        shape_type = shape_def[0]

        if shape_type == "rectangle":
            _, x, y, w, h = shape_def
            self._fill_rect(int(x), int(y), int(w), int(h))

        elif shape_type == "circle":
            _, cx, cy, r = shape_def
            self._fill_circle(int(cx), int(cy), int(r))

        elif shape_type == "line":
            _, x1, y1, x2, y2, thickness = shape_def
            self._draw_line(int(x1), int(y1), int(x2), int(y2), int(thickness))

    def text(self, text, x, y=None, size=None):
        """Draw text at position."""
        if isinstance(x, vec2):
            y = int(x.y)
            x = int(x.x)
        else:
            x, y = int(x), int(y) if y is not None else 0

        gray = self._color_to_gray(self._pen)

        # Use proper bitmap font rendering if we have a font with render capability
        if self._font and hasattr(self._font, 'render_text'):
            self._font.render_text(
                self._buffer, self.width, self.height,
                str(text), int(x), int(y), gray
            )
        elif self._font and hasattr(self._font, '_pixel_font'):
            # _PixelFont wrapper - use its underlying font
            self._font._pixel_font.render_text(
                self._buffer, self.width, self.height,
                str(text), int(x), int(y), gray
            )
        else:
            # Fallback: use default winds font
            from emulator.mocks.pixel_font_data import winds
            winds.render_text(
                self._buffer, self.width, self.height,
                str(text), int(x), int(y), gray
            )

    def measure_text(self, text, size=None):
        """Measure text dimensions."""
        char_w = 4
        char_h = 6
        if self._font and hasattr(self._font, 'height'):
            char_h = self._font.height
            char_w = int(char_h * 0.7)
        return (len(str(text)) * char_w, char_h)

    def blit(self, src, src_rect=None, dst_rect=None):
        """Blit (copy) from source image."""
        if not isinstance(src, image):
            return

        # Source region
        if src_rect:
            sx, sy, sw, sh = src_rect.x, src_rect.y, src_rect.w, src_rect.h
        else:
            sx, sy, sw, sh = 0, 0, src.width, src.height

        # Destination position
        if dst_rect:
            dx, dy = dst_rect.x, dst_rect.y
        else:
            dx, dy = 0, 0

        for row in range(sh):
            for col in range(sw):
                src_x, src_y = sx + col, sy + row
                dst_x, dst_y = dx + col, dy + row
                if (0 <= src_x < src.width and 0 <= src_y < src.height and
                        0 <= dst_x < self.width and 0 <= dst_y < self.height):
                    self._buffer[dst_y * self.width + dst_x] = \
                        src._buffer[src_y * src.width + src_x]

    def window(self, x, y, w, h):
        """Create a view/window into this image."""
        # Return a new image that references a portion of this one
        win = image(w, h)
        win._parent = self
        win._offset = (x, y)
        return win

    def _color_to_gray(self, col):
        """Convert RGBA color to grayscale byte."""
        if isinstance(col, int):
            if col > 0xFFFFFF:
                # RGBA format
                r = (col >> 24) & 0xFF
                g = (col >> 16) & 0xFF
                b = (col >> 8) & 0xFF
            else:
                # RGB format
                r = (col >> 16) & 0xFF
                g = (col >> 8) & 0xFF
                b = col & 0xFF
            # Convert to grayscale
            return int(0.299 * r + 0.587 * g + 0.114 * b)
        return 128  # Default gray for patterns/brushes

    def rectangle(self, x, y, w, h):
        """Draw a filled rectangle (public API)."""
        self._fill_rect(int(x), int(y), int(w), int(h))

    def _fill_rect(self, x, y, w, h):
        """Fill a rectangle."""
        gray = self._color_to_gray(self._pen)
        for dy in range(max(0, y), min(self.height, y + h)):
            for dx in range(max(0, x), min(self.width, x + w)):
                self._buffer[dy * self.width + dx] = gray

    def _fill_circle(self, cx, cy, r):
        """Fill a circle."""
        gray = self._color_to_gray(self._pen)
        for dy in range(max(0, cy - r), min(self.height, cy + r + 1)):
            for dx in range(max(0, cx - r), min(self.width, cx + r + 1)):
                if (dx - cx) ** 2 + (dy - cy) ** 2 <= r ** 2:
                    self._buffer[dy * self.width + dx] = gray

    def _draw_line(self, x1, y1, x2, y2, thickness=1):
        """Draw a line using Bresenham's algorithm."""
        gray = self._color_to_gray(self._pen)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if 0 <= x1 < self.width and 0 <= y1 < self.height:
                self._buffer[y1 * self.width + x1] = gray
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy


# --- Pixel Font ---

class _PixelFont:
    """Pixel font class for bitmap fonts."""

    def __init__(self, height=6):
        self.height = height

    @staticmethod
    def load(filename):
        """Load a pixel font from file."""
        if get_state().get("trace"):
            print(f"[pixel_font] Loading {filename}")
        # Return a basic font with estimated height
        height = 6
        if "sins" in filename or "smart" in filename:
            height = 7
        elif "winds" in filename:
            height = 5
        return _PixelFont(height)


pixel_font = _PixelFont


# --- Vector Font ---

class font:
    """Vector font class."""

    def __init__(self, size=12):
        self.size = size

    @staticmethod
    def load(filename):
        """Load a vector font from file."""
        if get_state().get("trace"):
            print(f"[font] Loading {filename}")
        return font()


# --- ROMFonts ---

class _ROMFonts:
    """ROM font accessor."""

    def __getattr__(self, key):
        return _PixelFont(7)

    def __dir__(self):
        return ["sins", "smart", "winds"]


rom_font = _ROMFonts()


# --- Display wrapper ---

class _Display:
    """Display wrapper that manages the blinky display."""

    def __init__(self):
        self._blinky = None

    def _get_blinky(self):
        if self._blinky is None:
            state = get_state()
            self._blinky = state.get("blinky_display")
        return self._blinky

    def update(self):
        """Update the display."""
        blinky = self._get_blinky()
        if blinky:
            blinky.update()

    def set_brightness(self, value):
        """Set display brightness."""
        blinky = self._get_blinky()
        if blinky:
            blinky.set_brightness(value)


display = _Display()


# --- RTC stub ---

class _RTC:
    """RTC stub with timer state tracking."""

    def __init__(self):
        self._timer_seconds = 0
        self._timer_enabled = False
        self._timer_flag = False

    def datetime(self, dt=None):
        if dt:
            return
        t = _time.localtime()
        return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday)

    def clear_timer_flag(self):
        self._timer_flag = False

    def enable_timer_interrupt(self, enable):
        self._timer_enabled = bool(enable)

    def set_timer(self, seconds):
        self._timer_seconds = seconds


rtc = _RTC()


# --- Helper functions ---

def run(update, init=None, on_exit=None, auto_clear=True):
    """Main run loop for badgeware apps."""
    state = get_state()

    if init:
        init()

    try:
        while state.get("running", True):
            # Check max frames
            max_frames = state.get("max_frames", 0)
            if max_frames > 0 and state.get("frame_count", 0) >= max_frames:
                break

            if auto_clear:
                screen.pen = color.black
                screen.clear()
                screen.pen = color.white

            io.poll()
            result = update()
            if result is not None:
                return result

            display.update()

            # Small delay to prevent CPU spinning
            _time.sleep(0.016)  # ~60 FPS

    except KeyboardInterrupt:
        pass
    finally:
        if on_exit:
            on_exit()


def fatal_error(title, error):
    """Display a fatal error message."""
    print(f"FATAL ERROR: {title}")
    print(error)


def set_brightness(value):
    """Set display brightness."""
    display.set_brightness(value)


def set_case_led(led, value):
    """Set a case LED brightness."""
    if get_state().get("trace"):
        print(f"[badgeware] Case LED {led} = {value}")


def get_case_led(led):
    """Get a case LED brightness."""
    return 0.0


# --- Setup builtins ---

def _setup_builtins():
    """Install badgeware primitives into builtins."""
    # These need to be available globally in badgeware apps
    builtins.color = color
    builtins.shape = shape
    builtins.brush = brush
    builtins.rect = rect
    builtins.vec2 = vec2
    builtins.image = image
    builtins.font = font
    builtins.pixel_font = pixel_font
    builtins.rom_font = rom_font
    builtins.io = io
    builtins.display = display
    builtins.rtc = rtc

    # Helper functions
    builtins.run = run
    builtins.fatal_error = fatal_error
    builtins.set_brightness = set_brightness
    builtins.set_case_led = set_case_led
    builtins.get_case_led = get_case_led
    builtins.scroll_text = scroll_text
    builtins.clamp = clamp
    builtins.rnd = rnd
    builtins.frnd = frnd
    builtins.mode = mode
    builtins.HIRES = HIRES
    builtins.LORES = LORES
    builtins.load_font = load_font
    builtins.State = State
    builtins.get_battery_level = get_battery_level
    builtins.get_usb_connected = get_usb_connected
    builtins.is_charging = is_charging


# Create the screen once blinky is available
screen = None


def _create_screen():
    """Create the screen object after blinky is initialized."""
    global screen
    from emulator.mocks import blinky as blinky_mod
    screen = image(blinky_mod.WIDTH, blinky_mod.HEIGHT)
    builtins.screen = screen
    return screen


# --- State class ---

class State:
    """App state persistence."""

    @staticmethod
    def delete(app):
        pass

    @staticmethod
    def save(app, data):
        pass

    @staticmethod
    def modify(app, data):
        pass

    @staticmethod
    def load(app, defaults):
        return False


# --- Scroll text ---

def scroll_text(text, font_face=None, bg=None, fg=None, target=None, speed=25,
                continuous=False, font_size=None):
    """Create scrolling text animation."""
    fg = fg or color.rgb(128, 128, 128)
    target = target or screen

    t_start = io.ticks
    text_width = len(text) * 4  # Approximate

    def update():
        elapsed = io.ticks - t_start
        scroll_pos = int((elapsed / 1000) * speed) % (text_width + target.width)

        if bg is not None:
            target.pen = bg
            target.clear()
        target.pen = fg
        target.text(text, target.width - scroll_pos, target.height // 2 - 3)
        return elapsed / 1000

    return update


# --- Clamp ---

def clamp(v, vmin, vmax):
    """Clamp value to range."""
    return max(vmin, min(v, vmax))


# --- Random helpers ---

import random as _random


def rnd(v1, v2=None):
    """Random integer."""
    if v2 is not None:
        return _random.randint(v1, v2)
    return _random.randint(0, v1)


def frnd(v1, v2=None):
    """Random float."""
    if v2 is not None:
        return _random.uniform(v1, v2)
    return _random.uniform(0, v1)


# --- Display modes ---

HIRES = 1
LORES = 0


def mode(m, force=False):
    """Set display mode (no-op in emulator)."""
    pass


# --- File helpers ---

def file_exists(path):
    """Check if a file exists."""
    import os
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def is_dir(path):
    """Check if a path is a directory."""
    import os
    try:
        flags = os.stat(path)
        return flags[0] & 0x4000
    except:
        return False


def load_font(font_file):
    """Load a font file."""
    return pixel_font.load(font_file)


def get_battery_level():
    """Get battery level as percentage (0-100)."""
    battery = get_state().get("battery")
    if battery:
        return battery.get_level()
    return 50


def get_usb_connected():
    """Check if USB power is connected."""
    battery = get_state().get("battery")
    if battery:
        return battery._usb_connected
    return True


def is_charging():
    """Check if the battery is currently charging.

    On real hardware: returns True when USB is connected and CHARGE_STAT
    pin (pin 25) is low (active-low signal from charge controller).
    """
    battery = get_state().get("battery")
    if battery:
        return battery._charging
    return False
