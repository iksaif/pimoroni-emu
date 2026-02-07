"""Image comparison utilities for visual regression testing."""

from pathlib import Path
from typing import Optional, Tuple, Union
from PIL import Image
import math

from emulator import get_state, get_display


def compare_images(
    image1: Union[str, Path, Image.Image],
    image2: Union[str, Path, Image.Image],
    threshold: float = 0.99,
) -> Tuple[bool, float, Optional[Image.Image]]:
    """Compare two images and return similarity.

    Args:
        image1: First image (path or PIL Image)
        image2: Second image (path or PIL Image)
        threshold: Similarity threshold (0-1, default 0.99)

    Returns:
        Tuple of (match: bool, similarity: float, diff_image: Image or None)
    """
    # Load images
    if isinstance(image1, (str, Path)):
        img1 = Image.open(image1).convert("RGB")
    else:
        img1 = image1.convert("RGB")

    if isinstance(image2, (str, Path)):
        img2 = Image.open(image2).convert("RGB")
    else:
        img2 = image2.convert("RGB")

    # Check dimensions match
    if img1.size != img2.size:
        # Create diff showing size mismatch
        max_w = max(img1.width, img2.width)
        max_h = max(img1.height, img2.height)
        diff = Image.new("RGB", (max_w, max_h), (255, 0, 0))
        return False, 0.0, diff

    # Calculate pixel-by-pixel difference
    pixels1 = img1.load()
    pixels2 = img2.load()

    width, height = img1.size
    total_pixels = width * height
    matching_pixels = 0
    diff_pixels = []

    for y in range(height):
        for x in range(width):
            p1 = pixels1[x, y]
            p2 = pixels2[x, y]

            # Calculate color distance
            dr = abs(p1[0] - p2[0])
            dg = abs(p1[1] - p2[1])
            db = abs(p1[2] - p2[2])
            distance = math.sqrt(dr * dr + dg * dg + db * db)

            # Pixels are "matching" if very close (allow for anti-aliasing)
            if distance < 10:  # ~4% tolerance per channel
                matching_pixels += 1
                diff_pixels.append((0, 0, 0))  # Black = match
            else:
                # Highlight difference
                intensity = min(255, int(distance))
                diff_pixels.append((255, intensity, intensity))  # Red = diff

    similarity = matching_pixels / total_pixels if total_pixels > 0 else 0

    # Create diff image
    diff = Image.new("RGB", (width, height))
    diff.putdata(diff_pixels)

    match = similarity >= threshold

    if get_state().get("trace"):
        print(f"[compare] Similarity: {similarity:.4f}, threshold: {threshold}, match: {match}")

    return match, similarity, diff


def assert_display_matches(
    expected_path: Union[str, Path],
    threshold: float = 0.99,
    save_diff: Optional[str] = None,
) -> bool:
    """Assert that current display matches expected image.

    Args:
        expected_path: Path to expected image
        threshold: Similarity threshold (0-1)
        save_diff: Optional path to save diff image on failure

    Returns:
        True if match

    Raises:
        AssertionError if no match
    """
    display = get_display()
    if display is None:
        raise AssertionError("No display available")

    # Get current display as image
    surface = display.get_surface()
    if surface is None:
        raise AssertionError("Display has no content")

    # Convert to PIL Image if needed
    if hasattr(surface, "load"):
        current = surface
    else:
        # Assume pygame surface
        import pygame
        data = pygame.image.tostring(surface, "RGB")
        current = Image.frombytes("RGB", surface.get_size(), data)

    # Load expected
    expected_path = Path(expected_path)
    if not expected_path.exists():
        # Save current as expected for first run
        current.save(expected_path)
        print(f"[compare] Created expected image: {expected_path}")
        return True

    # Compare
    match, similarity, diff = compare_images(current, expected_path, threshold)

    if not match:
        if save_diff:
            diff.save(save_diff)
            print(f"[compare] Saved diff to: {save_diff}")

        raise AssertionError(
            f"Display does not match expected image. "
            f"Similarity: {similarity:.4f}, required: {threshold}"
        )

    return True


def create_reference(output_path: Union[str, Path]) -> bool:
    """Save current display as reference image.

    Args:
        output_path: Path to save reference image

    Returns:
        True if successful
    """
    display = get_display()
    if display is None:
        print("[compare] No display available")
        return False

    return display.screenshot(str(output_path))
