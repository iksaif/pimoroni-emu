"""Device abstraction for Presto only.

The Tufty 2350 ships with Pimoroni's badgeware firmware (different API
surface: image/screen/badge globals, no `picographics` module). Use
apps/wifi_health_tufty/ for a Tufty-native port — this app stays
Presto-only.

Exposes a Device object with:
  display              the PicoGraphics instance
  width, height        display bounds
  has_touch            True on Presto
  status_leds(rgb)     paint the Presto ring
  read_touch()         (x, y, pressed) tuple
  update()             flush display + poll touch
"""


class Device:
    def __init__(self):
        self.kind = None
        self._presto = None
        self._display = None
        self.has_touch = False
        self.width = 0
        self.height = 0

    # ── Back RGB ring (Presto only) ────────────────────────────────────
    NUM_LEDS = 7

    def set_leds(self, colors, scale=4):
        """Paint the back RGB ring.

        Accepts an iterable of up to NUM_LEDS (r, g, b) tuples. `scale`
        divides each channel — bumps tones down to a wall-bias level
        rather than glare.

        The upstream Presto module only exposes set_led_rgb (it flushes
        immediately), so we don't try to call set_led_brightness or
        update_leds here even though the emulator mock has them.
        """
        if self._presto is None:
            return
        for i, rgb in enumerate(list(colors)[: self.NUM_LEDS]):
            if rgb is None:
                continue
            r, g, b = (max(0, min(255, c)) // scale for c in rgb)
            self._presto.set_led_rgb(i, r, g, b)

    def status_leds(self, rgb):
        """Paint all LEDs in the same colour (back-compat helper)."""
        self.set_leds([rgb] * self.NUM_LEDS)

    # ── Input ──────────────────────────────────────────────────────────
    def read_touch(self):
        """Return (x, y, pressed). Pressed is False on devices without touch."""
        if self._presto is None:
            return 0, 0, False
        self._presto.touch_poll()
        t = self._presto.touch
        return int(t.x), int(t.y), bool(t.state)

    def read_buttons(self):
        """Presto has no physical buttons — always empty."""
        return {}

    # ── Frame flush ────────────────────────────────────────────────────
    def update(self):
        if self._presto is not None:
            self._presto.update()
        else:
            self._display.update()

    def set_backlight(self, brightness):
        if self._presto is not None:
            self._presto.set_backlight(brightness)
        elif hasattr(self._display, "set_backlight"):
            self._display.set_backlight(brightness)


def detect():
    """Auto-detect the host device and return a wired-up Device."""
    dev = Device()

    # Presto (touch + ring LEDs)
    try:
        from presto import Presto
        # full_res=True → 480x480 framebuffer; both PicoGraphics drawing and
        # FT6236 touch coordinates use the same coordinate space. With the
        # default (full_res=False) the framebuffer is 240x240 and the SDK
        # scales touch reads by /2 to match — see vendor/presto/modules/
        # py_frozen/touch.py:_read_touch. We pick full_res so the CRT theme
        # has enough pixels for the dashed dividers and the 48-cell heatmap.
        presto = Presto(full_res=True)
        dev.kind = "presto"
        dev._presto = presto
        dev._display = presto.display
        dev.has_touch = True
        dev.width, dev.height = presto.display.get_bounds()
        return dev
    except ImportError:
        pass

    raise RuntimeError(
        "WiFi Health Monitor (Presto edition) requires the presto module. "
        "For Tufty 2350, use the apps/wifi_health_tufty/ variant."
    )
