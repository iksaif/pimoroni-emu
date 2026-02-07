"""Mock implementation of pngdec module for PNG decoding.

Uses Pillow to decode PNG images and render them to PicoGraphics displays.
"""

from typing import Optional
from emulator import get_state


class PNG:
    """PNG decoder that renders to a PicoGraphics display."""

    def __init__(self, display):
        """Initialize with a PicoGraphics display.

        Args:
            display: PicoGraphics instance to render to
        """
        self._display = display
        self._image = None
        self._width = 0
        self._height = 0
        self._file_path = None

    def open_file(self, filename: str):
        """Open a PNG file for decoding.

        Args:
            filename: Path to PNG file

        Raises:
            OSError: If file cannot be opened
        """
        try:
            from PIL import Image
            self._image = Image.open(filename)
            self._width = self._image.width
            self._height = self._image.height
            self._file_path = filename

            state = get_state()
            if state.get("trace"):
                print(f"[pngdec] Opened {filename} ({self._width}x{self._height})")
        except Exception as e:
            raise OSError(f"Failed to open PNG: {e}")

    def open_RAM(self, data: bytes):
        """Open PNG data from memory.

        Args:
            data: PNG image data as bytes

        Raises:
            RuntimeError: If data cannot be decoded
        """
        try:
            from PIL import Image
            import io
            self._image = Image.open(io.BytesIO(data))
            self._width = self._image.width
            self._height = self._image.height
            self._file_path = None

            state = get_state()
            if state.get("trace"):
                print(f"[pngdec] Opened from RAM ({self._width}x{self._height})")
        except Exception as e:
            raise RuntimeError(f"Failed to decode PNG: {e}")

    def decode(self, x: int = 0, y: int = 0, scale: int = 1, mode: int = 0, rotate: int = 0):
        """Decode and render the PNG to the display.

        Args:
            x: X position to render at
            y: Y position to render at
            scale: Scale factor (1 = original size, negative for downscale)
            mode: Rendering mode
            rotate: Rotation angle
        """
        if self._image is None:
            raise RuntimeError("No PNG file opened")

        state = get_state()
        if state.get("trace"):
            print(f"[pngdec] decode at ({x}, {y}), scale={scale}")

        # Handle scaling
        if scale < 0:
            # Negative scale means divide dimensions
            scale_factor = 1 / abs(scale)
        else:
            scale_factor = scale if scale > 0 else 1

        # Calculate dimensions
        width = int(self._width * scale_factor)
        height = int(self._height * scale_factor)

        # Convert to RGB if necessary
        img = self._image
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")

        # Resize if needed
        if scale_factor != 1:
            from PIL import Image
            img = img.resize((width, height), Image.Resampling.NEAREST)

        # Handle rotation
        if rotate != 0:
            from PIL import Image
            if rotate == 90:
                img = img.transpose(Image.Transpose.ROTATE_90)
            elif rotate == 180:
                img = img.transpose(Image.Transpose.ROTATE_180)
            elif rotate == 270:
                img = img.transpose(Image.Transpose.ROTATE_270)

        # Render to display
        self._render_to_display(img, x, y)

    def _render_to_display(self, img, x: int, y: int):
        """Render a PIL image to the PicoGraphics display."""
        display_width, display_height = self._display.get_bounds()

        for py in range(img.height):
            if y + py < 0 or y + py >= display_height:
                continue
            for px in range(img.width):
                if x + px < 0 or x + px >= display_width:
                    continue

                pixel = img.getpixel((px, py))

                # Handle different image modes
                if img.mode == "RGBA":
                    r, g, b, a = pixel
                    if a < 128:  # Skip transparent pixels
                        continue
                elif img.mode == "RGB":
                    r, g, b = pixel
                elif img.mode == "L":
                    # Grayscale
                    r = g = b = pixel
                else:
                    continue

                # Create pen and draw pixel
                pen = self._display.create_pen(r, g, b)
                self._display.set_pen(pen)
                self._display.pixel(x + px, y + py)

    def get_width(self) -> int:
        """Get image width."""
        return self._width

    def get_height(self) -> int:
        """Get image height."""
        return self._height

    def get_palette(self):
        """Get image palette (if indexed)."""
        if self._image and self._image.mode == "P":
            return self._image.getpalette()
        return None
