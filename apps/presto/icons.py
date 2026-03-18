"""Emoji icon loader for PicoGraphics displays.

Downloads emoji PNGs from Twemoji CDN on first use, caches them locally
(SD card on real hardware, filesystem in emulator), and renders via pngdec.

Usage:
    from icons import IconLoader
    icons = IconLoader(display, size=24, cache_dir="/sd/icons")
    icons.draw("rocket", x, y)
    icons.draw("1f680", x, y)  # by codepoint

Twemoji graphics are CC-BY 4.0 (https://github.com/jdecked/twemoji)
"""

import os

# Tag -> Unicode codepoint mapping (curated for kids/history content)
EMOJI_MAP = {
    # Space & science
    "rocket": "1f680",
    "star": "2b50",
    "globe": "1f30d",
    "telescope": "1f52d",
    "satellite": "1f6f0",
    "moon": "1f319",
    "sun": "2600",
    "atom": "269b",
    "microscope": "1f52c",
    "dna": "1f9ec",
    "magnet": "1f9f2",
    "comet": "2604",
    # Nature & animals
    "tree": "1f332",
    "flower": "1f33b",
    "whale": "1f40b",
    "dinosaur": "1f995",
    "butterfly": "1f98b",
    "penguin": "1f427",
    "dolphin": "1f42c",
    "earth": "1f30e",
    "volcano": "1f30b",
    "rainbow": "1f308",
    "ocean": "1f30a",
    # Sports & games
    "trophy": "1f3c6",
    "medal": "1f3c5",
    "soccer": "26bd",
    "basketball": "1f3c0",
    # People & culture
    "crown": "1f451",
    "book": "1f4d6",
    "scroll": "1f4dc",
    "pen": "1f58a",
    "paint": "1f3a8",
    "music": "1f3b5",
    "movie": "1f3ac",
    "theater": "1f3ad",
    "graduation": "1f393",
    # Transport & exploration
    "ship": "1f6a2",
    "airplane": "2708",
    "train": "1f682",
    "compass": "1f9ed",
    "map": "1f5fa",
    "flag": "1f3f3",
    "anchor": "2693",
    # Building & invention
    "gear": "2699",
    "lightbulb": "1f4a1",
    "hammer": "1f528",
    "computer": "1f4bb",
    "phone": "1f4f1",
    "radio": "1f4fb",
    "camera": "1f4f7",
    # Food & celebration
    "cake": "1f382",
    "party": "1f389",
    "balloon": "1f388",
    "gift": "1f381",
    # Misc
    "heart": "2764",
    "fire": "1f525",
    "sparkles": "2728",
    "check": "2705",
    "clock": "1f552",
    "peace": "262e",
    "handshake": "1f91d",
    "thinking": "1f914",
    "wow": "1f62e",
    "cool": "1f60e",
}

# Twemoji CDN base URL (72x72 PNGs)
_CDN_URL = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{}.png"


class IconLoader:
    """Downloads, caches, and renders emoji icons on PicoGraphics."""

    def __init__(self, display, size=24, cache_dir="icon_cache"):
        """
        Args:
            display: PicoGraphics display instance
            size: Target icon size in pixels (icons are downscaled to this)
            cache_dir: Directory to cache downloaded PNGs
        """
        self._display = display
        self._size = size
        self._cache_dir = cache_dir
        self._png = None  # lazy init pngdec
        self._available = {}  # codepoint -> cached file path
        self._failed = set()  # codepoints that failed to download

        # Create cache dir (and parents) if it doesn't exist
        try:
            os.mkdir(cache_dir)
        except OSError:
            pass  # already exists or parent missing
        # Verify it exists
        try:
            os.listdir(cache_dir)
        except OSError:
            # Try creating parent too
            try:
                parts = cache_dir.rsplit("/", 1)
                if len(parts) == 2 and parts[0]:
                    os.mkdir(parts[0])
                os.mkdir(cache_dir)
            except OSError:
                pass
        print("[icons] cache_dir:", cache_dir)

        # Scan cache for existing icons
        try:
            for f in os.listdir(cache_dir):
                if f.endswith(".png"):
                    cp = f[:-4]  # strip .png
                    self._available[cp] = cache_dir + "/" + f
            if self._available:
                print("[icons] found", len(self._available), "cached on disk")
        except OSError:
            pass

    def _get_png(self):
        """Lazy-init pngdec."""
        if self._png is None:
            from pngdec import PNG
            self._png = PNG(self._display)
        return self._png

    def _resolve(self, name):
        """Resolve a name or codepoint to a codepoint string."""
        # Direct codepoint (hex string)?
        if name in self._available:
            return name
        # Known tag?
        cp = EMOJI_MAP.get(name.lower())
        if cp:
            return cp
        # Assume it's a codepoint already
        return name.lower()

    def _download(self, codepoint):
        """Download a single emoji PNG from Twemoji CDN and cache it."""
        url = _CDN_URL.format(codepoint)
        cache_path = self._cache_dir + "/" + codepoint + ".png"

        if codepoint in self._failed:
            return False
        try:
            import urequests
            print("[icons] GET", url)
            resp = urequests.get(url)
            print("[icons] status:", resp.status_code)
            if resp.status_code == 200:
                data = resp.content
                with open(cache_path, "wb") as f:
                    f.write(data)
                self._available[codepoint] = cache_path
                print("[icons] cached:", cache_path)
                resp.close()
                return True
            resp.close()
        except Exception as e:
            print("[icons] download error:", e)
        self._failed.add(codepoint)
        return False

    def ensure(self, name):
        """Make sure an icon is cached. Returns True if available."""
        cp = self._resolve(name)
        if cp in self._available:
            return True
        return self._download(cp)

    def ensure_many(self, names):
        """Download multiple icons. Returns count of successful downloads."""
        count = 0
        for name in names:
            if self.ensure(name):
                count += 1
        return count

    def draw(self, name, x, y):
        """Draw an icon at (x, y). Downloads if not cached. Returns icon width or 0."""
        cp = self._resolve(name)
        if cp not in self._available:
            if not self._download(cp):
                return 0

        try:
            path = self._available[cp]
            print("[icons] load", path)
            png = self._get_png()
            png.open_file(path)
            self._actual_size = png.get_width()
            png.decode(x, y)
            return self._actual_size
        except Exception as e:
            print("[icons] draw error:", cp, e)
            return 0

    def has(self, name):
        """Check if an icon is cached (without downloading)."""
        cp = self._resolve(name)
        return cp in self._available

    @property
    def actual_size(self):
        """Last rendered icon size (may differ from target on real hw)."""
        return getattr(self, "_actual_size", None)

    @property
    def size(self):
        return self._size

    @staticmethod
    def list_tags():
        """Return all known emoji tag names."""
        return sorted(EMOJI_MAP.keys())
