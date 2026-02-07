"""Screenshot and recording utilities."""

from pathlib import Path
from typing import Optional
from emulator import get_state, get_display


_recording = False
_recording_dir: Optional[Path] = None
_recording_frame = 0


def screenshot(filename: str) -> bool:
    """Save current display to file.

    Args:
        filename: Output filename (PNG recommended)

    Returns:
        True if successful, False otherwise
    """
    display = get_display()
    if display is None:
        print("[capture] No display available")
        return False

    return display.screenshot(filename)


def start_recording(output_dir: str):
    """Start recording frames to directory.

    Each call to display.update() will save a frame as frame_NNNNN.png.

    Args:
        output_dir: Directory to save frames to
    """
    global _recording, _recording_dir, _recording_frame

    _recording_dir = Path(output_dir)
    _recording_dir.mkdir(parents=True, exist_ok=True)
    _recording = True
    _recording_frame = 0

    # Enable autosave on display
    display = get_display()
    if display:
        display.set_autosave(output_dir)

    if get_state().get("trace"):
        print(f"[capture] Started recording to {output_dir}")


def stop_recording() -> int:
    """Stop recording and return number of frames captured.

    Returns:
        Number of frames recorded
    """
    global _recording, _recording_dir

    display = get_display()
    if display:
        display.set_autosave(None)

    frames = _recording_frame if _recording else 0
    _recording = False
    _recording_dir = None

    if get_state().get("trace"):
        print(f"[capture] Stopped recording. {frames} frames captured.")

    return frames


def is_recording() -> bool:
    """Check if currently recording."""
    return _recording


def get_frame_count() -> int:
    """Get current frame count."""
    display = get_display()
    if display:
        return display.get_frame_count()
    return 0
