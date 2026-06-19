"""Base display renderer class."""

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from emulator import get_state

# ASCII grayscale ramp (darkest to brightest)
ASCII_RAMP = " .:-=+*#%@"

# Font cache for safe_font()
_font_cache: dict = {}


class _BitmapPygameFont:
    """Minimal pygame ``Font`` stand-in backed by the built-in ``bitmap8``
    glyphs.

    Used when the real ``pygame.font`` backend is unavailable — e.g. on
    Python 3.14 the pygame 2.6 / SDL_ttf binding fails to import, so
    ``pygame.font`` is a ``MissingModule`` and every emulator-chrome label
    (button names, key hints, status text) would silently render as
    nothing. This keeps those labels visible by rasterising the same
    bitmap font the PicoGraphics mock uses, onto a pygame surface.

    Implements just the slice of the Font API the renderers use:
    ``render(text, antialias, color)`` → Surface and ``size(text)``.
    """

    def __init__(self, pg, size: int):
        from emulator.mocks.fonts import get_font
        self._pg = pg
        self._font = get_font("bitmap8")  # 8px tall, columns LSB=top
        # Scale the 8px glyphs to roughly match the requested point size.
        self._scale = max(1, round(size / 8))
        self._spacing = 1
        self._cache: dict = {}

    def render(self, text, antialias=True, color=(255, 255, 255), background=None):
        text = str(text)
        rgb = tuple(color[:3])
        key = (text, rgb, self._scale)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        f = self._font
        sc = self._scale
        sp = self._spacing
        w = max(1, f.measure_text(text, sp) * sc)
        h = f.height * sc
        surf = self._pg.Surface((w, h), self._pg.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        cx = 0
        for ch in text:
            columns, char_w = f.get_char_data(ch)
            for ci in range(char_w):
                if ci >= len(columns):
                    break
                col_byte = columns[ci]
                for row in range(f.height):
                    if col_byte & (1 << row):  # LSB = top row
                        surf.fill(rgb, ((cx + ci) * sc, row * sc, sc, sc))
            cx += char_w + sp

        self._cache[key] = surf
        return surf

    def size(self, text):
        text = str(text)
        return (self._font.measure_text(text, self._spacing) * self._scale,
                self._font.height * self._scale)


def safe_font(pg, name: str = "monospace", size: int = 14, bold: bool = False):
    """Get a font for drawing emulator chrome (labels, status text).

    Prefers a real pygame font. If the pygame font backend is unavailable
    (notably the broken pygame/SDL_ttf binding on Python 3.14), falls back
    to a bitmap-glyph stand-in so labels still render rather than silently
    disappearing. Always returns a usable font object.
    """
    key = (name, size, bold)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached

    font = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            font = pg.font.SysFont(name, size, bold=bold)
        except (NotImplementedError, ImportError, AttributeError):
            try:
                # Fallback: use pygame's default font
                font = pg.font.Font(None, size)
            except (NotImplementedError, ImportError, AttributeError):
                pass

    if font is None:
        # No real font backend — use the bitmap fallback so chrome labels
        # (e.g. the button names) remain legible.
        try:
            font = _BitmapPygameFont(pg, size)
        except Exception:  # noqa: BLE001 — last resort, never block rendering
            font = None

    _font_cache[key] = font
    return font


class BaseDisplay(ABC):
    """Base class for display renderers."""

    def __init__(self, device, headless: bool = False):
        self.device = device
        self.headless = headless
        self._surface = None
        self._window = None
        self._frame_count = 0
        self._autosave_dir: Optional[Path] = None
        self._text_output: bool = False
        self._text_output_file: Optional[Path] = None

        # Last rendered framebuffer (for screenshots)
        self._last_buffer: Optional[List[List[int]]] = None

    @abstractmethod
    def init(self):
        """Initialize display (create pygame window if not headless)."""
        pass

    @abstractmethod
    def render(self, buffer: List[List[int]]):
        """Render framebuffer to display/surface."""
        pass

    @abstractmethod
    def get_surface(self):
        """Get pygame surface (or PIL Image in headless mode)."""
        pass

    def set_autosave(self, directory: Optional[str]):
        """Enable autosave of frames to directory."""
        if directory:
            self._autosave_dir = Path(directory)
            self._autosave_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._autosave_dir = None

    def set_text_output(self, enabled: bool = True, output_file: Optional[str] = None):
        """Enable text/ASCII output mode for debugging."""
        self._text_output = enabled
        if output_file:
            self._text_output_file = Path(output_file)
        else:
            self._text_output_file = None

    def screenshot(self, filename: str):
        """Save current display to file."""
        if self._last_buffer is None:
            return False

        img = self._buffer_to_image(self._last_buffer)
        img.save(filename)

        if get_state().get("trace"):
            print(f"[Display] Screenshot saved: {filename}")

        return True

    def _buffer_to_image(self, buffer: List[List[int]]) -> Image.Image:
        """Convert framebuffer to PIL Image."""
        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        img = Image.new("RGB", (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                color = buffer[y][x]
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                pixels[x, y] = (r, g, b)

        return img

    def _autosave_frame(self):
        """Save frame if autosave is enabled."""
        if self._autosave_dir and self._last_buffer:
            filename = self._autosave_dir / f"frame_{self._frame_count:05d}.png"
            self.screenshot(str(filename))

        # Output text representation
        if self._text_output and self._last_buffer:
            self._output_text_frame()

    def _output_text_frame(self):
        """Output frame as ASCII art with metadata."""
        if not self._last_buffer:
            return

        buffer = self._last_buffer
        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        # Build output
        lines = []
        lines.append(f"=== Frame {self._frame_count} ===")
        lines.append(f"Size: {width}x{height}")
        lines.append(f"Device: {self.device.name}")
        lines.append("")

        # ASCII art representation
        for y in range(height):
            row = ""
            for x in range(width):
                color = buffer[y][x]
                # Convert to grayscale
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)

                # Map to ASCII character
                idx = int(gray / 256 * len(ASCII_RAMP))
                idx = min(idx, len(ASCII_RAMP) - 1)
                row += ASCII_RAMP[idx]
            lines.append(row)

        lines.append("")

        # Output to file or stdout
        output = "\n".join(lines)
        if self._text_output_file:
            mode = "a" if self._frame_count > 1 else "w"
            with open(self._text_output_file, mode) as f:
                f.write(output + "\n")
        else:
            print(output)

    def buffer_to_ascii(self, max_width: int = 80) -> str:
        """Convert current buffer to ASCII art string."""
        if not self._last_buffer:
            return "(no buffer)"

        buffer = self._last_buffer
        height = len(buffer)
        width = len(buffer[0]) if height > 0 else 0

        # Calculate scaling if needed
        scale = 1
        if width > max_width:
            scale = width // max_width + 1

        lines = []
        for y in range(0, height, scale):
            row = ""
            for x in range(0, width, scale):
                color = buffer[y][x]
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)

                idx = int(gray / 256 * len(ASCII_RAMP))
                idx = min(idx, len(ASCII_RAMP) - 1)
                row += ASCII_RAMP[idx]
            lines.append(row)

        return "\n".join(lines)

    def get_frame_count(self) -> int:
        """Get number of rendered frames."""
        return self._frame_count

    def _get_memory_info(self) -> Optional[Tuple[int, int]]:
        """Return (used, total) heap bytes, or None if tracking is off."""
        tracker = get_state().get("memory_tracker")
        if tracker is None:
            return None
        used = tracker.mem_alloc()
        return (used, used + tracker.mem_free())

    def close(self):
        """Close display."""
        pass


def draw_memory_bar(pg, surface, x: int, y: int, width: int, used: int, total: int):
    """Draw a heap-usage bar with label. Shared across all renderers.

    Args:
        pg: pygame module
        surface: pygame Surface to draw on
        x, y: top-left corner
        width: bar width in pixels
        used, total: heap bytes
    """
    bar_height = 10
    ratio = used / total if total > 0 else 0

    # Color: green → yellow → red
    if ratio < 0.5:
        r = int(ratio * 2 * 255)
        g = 200
    else:
        r = 255
        g = int((1 - ratio) * 2 * 200)
    bar_color = (r, g, 0)

    # Background track
    pg.draw.rect(surface, (50, 50, 55), (x, y, width, bar_height), border_radius=2)
    # Filled portion
    fill_w = max(1, int(width * ratio))
    pg.draw.rect(surface, bar_color, (x, y, fill_w, bar_height), border_radius=2)
    # Border
    pg.draw.rect(surface, (80, 80, 85), (x, y, width, bar_height), 1, border_radius=2)

    # Label
    used_kb = used / 1024
    total_kb = total / 1024
    label = f"Heap: {used_kb:.0f}/{total_kb:.0f}KB"
    font = safe_font(pg, "monospace", 10)
    if font:
        text = font.render(label, True, (180, 180, 180))
        surface.blit(text, (x, y + bar_height + 1))
