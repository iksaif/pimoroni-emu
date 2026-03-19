"""Display compatibility layer.

Provides a unified API that works on both PicoGraphics and Badgeware devices.
Import `get_display()` to get the right display wrapper for the current device.

PicoGraphics devices: Presto, Badger 2350, Inky Frame, Tufty 2040
Badgeware devices: Tufty 2350, Blinky 2350
"""


class PicoGraphicsDisplay:
    """Thin wrapper around PicoGraphics — mostly passthrough."""

    def __init__(self, pg_display, presto=None):
        self._d = pg_display
        self.presto = presto
        self.width, self.height = pg_display.get_bounds()
        self.is_badgeware = False

    def create_pen(self, r, g, b):
        return self._d.create_pen(r, g, b)

    def create_pen_hsv(self, h, s, v):
        return self._d.create_pen_hsv(h, s, v)

    def set_pen(self, pen):
        self._d.set_pen(pen)

    def clear(self):
        self._d.clear()

    def rectangle(self, x, y, w, h):
        self._d.rectangle(x, y, w, h)

    def circle(self, x, y, r):
        self._d.circle(int(x), int(y), int(r))

    def line(self, x1, y1, x2, y2, thickness=1):
        self._d.line(x1, y1, x2, y2, thickness)

    def triangle(self, x1, y1, x2, y2, x3, y3):
        self._d.triangle(x1, y1, x2, y2, x3, y3)

    def text(self, text, x, y, wrap=-1, scale=1, spacing=1):
        self._d.text(text, x, y, wrap, scale=scale, spacing=spacing)

    def measure_text(self, text, scale=1, spacing=1):
        return self._d.measure_text(text, scale=scale, spacing=spacing)

    def set_layer(self, layer):
        if hasattr(self._d, 'set_layer'):
            self._d.set_layer(layer)

    def update(self):
        if self.presto:
            self.presto.update()
        else:
            self._d.update()

    @property
    def raw(self):
        """Access the underlying PicoGraphics instance."""
        return self._d


class BadgewareDisplay:
    """Wrapper that adapts Badgeware's screen/shape/color API to our interface.

    On Badgeware, `screen`, `shape`, `color`, `badge`, `image`, `vec2`,
    `pixel_font`, and button constants are builtins (injected by the runtime).
    """

    def __init__(self):
        # These are builtins on Badgeware — access via builtins module
        import builtins
        self._screen = builtins.screen
        self._shape = builtins.shape
        self._color = builtins.color
        self.width = self._screen.width
        self.height = self._screen.height
        self.presto = None
        self.is_badgeware = True
        self._current_pen = None
        self._font_scale = 1  # used to approximate PicoGraphics scale

    def create_pen(self, r, g, b):
        return self._color.rgb(r, g, b)

    def create_pen_hsv(self, h, s, v):
        return self._color.hsv(h, s, v)

    def set_pen(self, pen):
        self._current_pen = pen
        self._screen.pen = pen

    def clear(self):
        self._screen.clear()

    def rectangle(self, x, y, w, h):
        self._screen.shape(self._shape.rectangle(x, y, w, h))

    def circle(self, x, y, r):
        self._screen.shape(self._shape.circle(x, y, r))

    def line(self, x1, y1, x2, y2, thickness=1):
        self._screen.shape(self._shape.line(x1, y1, x2, y2, thickness))

    def triangle(self, x1, y1, x2, y2, x3, y3):
        # Badgeware doesn't have triangle — draw 3 lines
        self._screen.shape(self._shape.line(x1, y1, x2, y2, 1))
        self._screen.shape(self._shape.line(x2, y2, x3, y3, 1))
        self._screen.shape(self._shape.line(x3, y3, x1, y1, 1))

    def text(self, text, x, y, wrap=-1, scale=1, spacing=1):
        # Badgeware uses pixel fonts, scale is handled by font size
        self._screen.text(str(text), x, y)

    def measure_text(self, text, scale=1, spacing=1):
        try:
            w, h = self._screen.measure_text(str(text))
            return w
        except Exception:
            return len(str(text)) * 6 * scale  # rough fallback

    def set_layer(self, layer):
        pass  # Badgeware doesn't have layers

    def update(self):
        pass  # Badgeware uses run(update) loop, display updates automatically

    @property
    def raw(self):
        return self._screen


def get_display():
    """Detect the platform and return the appropriate display wrapper.

    Returns:
        (display, presto) tuple where display is a PicoGraphicsDisplay or
        BadgewareDisplay, and presto is the Presto instance or None.
    """
    # Try Presto first (has its own display)
    try:
        from presto import Presto
        presto = Presto(full_res=True)
        return PicoGraphicsDisplay(presto.display, presto), presto
    except ImportError:
        pass

    # Try PicoGraphics (Badger, Inky Frame, Tufty 2040)
    try:
        from picographics import PicoGraphics
        return PicoGraphicsDisplay(PicoGraphics()), None
    except ImportError:
        pass

    # Try Badgeware (Tufty 2350, Blinky 2350)
    try:
        import badgeware
        badgeware.mode(badgeware.HIRES)
        return BadgewareDisplay(), None
    except ImportError:
        pass

    raise RuntimeError("No supported display found")
