"""Mock implementation of JPEG decoder for Pimoroni displays."""

from typing import Optional, Callable
from PIL import Image
import io
from emulator import get_state


# Scale constants
JPEG_SCALE_FULL = 0  # 1:1
JPEG_SCALE_HALF = 1  # 1:2
JPEG_SCALE_QUARTER = 2  # 1:4
JPEG_SCALE_EIGHTH = 3  # 1:8


class JPEG:
    """JPEG decoder using Pillow."""

    def __init__(self, graphics):
        self._graphics = graphics
        self._image: Optional[Image.Image] = None
        self._callback: Optional[Callable] = None

    def open_file(self, filename: str) -> int:
        """Open JPEG from file."""
        try:
            self._image = Image.open(filename)
            if self._image.mode != "RGB":
                self._image = self._image.convert("RGB")
            if get_state().get("trace"):
                print(f"[JPEG] Opened {filename}: {self._image.size}")
            return 1  # Success
        except Exception as e:
            if get_state().get("trace"):
                print(f"[JPEG] Failed to open {filename}: {e}")
            return 0  # Failure

    def open_RAM(self, data: bytes) -> int:
        """Open JPEG from memory."""
        try:
            self._image = Image.open(io.BytesIO(data))
            if self._image.mode != "RGB":
                self._image = self._image.convert("RGB")
            if get_state().get("trace"):
                print(f"[JPEG] Opened from RAM: {self._image.size}")
            return 1
        except Exception as e:
            if get_state().get("trace"):
                print(f"[JPEG] Failed to open from RAM: {e}")
            return 0

    def decode(
        self,
        x: int = 0,
        y: int = 0,
        scale: int = 0,
        dither: bool = False
    ) -> int:
        """Decode and render JPEG to display."""
        if self._image is None:
            return 0

        # Scale: 0=1:1, 1=1:2, 2=1:4, 3=1:8
        scale_factor = 1 << scale
        width = self._image.width // scale_factor
        height = self._image.height // scale_factor

        if scale_factor > 1:
            img = self._image.resize((width, height), Image.Resampling.LANCZOS)
        else:
            img = self._image

        # Render to graphics buffer
        pixels = img.load()
        for py in range(height):
            for px in range(width):
                r, g, b = pixels[px, py]
                pen = self._graphics.create_pen(r, g, b)
                self._graphics.set_pen(pen)
                self._graphics.pixel(x + px, y + py)

        if get_state().get("trace"):
            print(f"[JPEG] Decoded at ({x}, {y}), scale 1:{scale_factor}")

        return 1

    def get_width(self) -> int:
        """Get image width."""
        return self._image.width if self._image else 0

    def get_height(self) -> int:
        """Get image height."""
        return self._image.height if self._image else 0

    def set_callback(self, callback: Callable):
        """Set decode callback for progress reporting."""
        self._callback = callback
