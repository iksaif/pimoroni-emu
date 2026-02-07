"""Mock implementation of uos (MicroPython os) module.

Provides filesystem operations with path redirection for the emulator.
The root "/" is redirected to the app's base directory or a configured
virtual filesystem root.
"""

import os as _real_os
from pathlib import Path
from emulator import get_state


def _get_vfs_root() -> str:
    """Get the virtual filesystem root directory."""
    state = get_state()
    return state.get("vfs_root", "/tmp/badger_vfs")


def _translate_path(path: str) -> str:
    """Translate MicroPython absolute path to host filesystem path.

    Paths like "/badges/badge.txt" are redirected to the virtual filesystem.
    """
    if not path:
        return path

    # If it's an absolute path (starts with /)
    if path.startswith("/"):
        vfs_root = _get_vfs_root()
        translated = _real_os.path.join(vfs_root, path.lstrip("/"))

        state = get_state()
        if state.get("trace"):
            print(f"[uos] Translating '{path}' -> '{translated}'")

        return translated

    return path


def getcwd() -> str:
    """Get current working directory."""
    return _real_os.getcwd()


def chdir(path: str):
    """Change current directory."""
    _real_os.chdir(_translate_path(path))


def listdir(path: str = ".") -> list:
    """List directory contents."""
    return _real_os.listdir(_translate_path(path))


def mkdir(path: str, mode: int = 0o777):
    """Create a directory."""
    translated = _translate_path(path)
    Path(translated).parent.mkdir(parents=True, exist_ok=True)
    _real_os.mkdir(translated, mode)


def makedirs(path: str, mode: int = 0o777, exist_ok: bool = False):
    """Create directories recursively."""
    Path(_translate_path(path)).mkdir(parents=True, exist_ok=exist_ok)


def remove(path: str):
    """Remove a file."""
    _real_os.remove(_translate_path(path))


def rmdir(path: str):
    """Remove a directory."""
    _real_os.rmdir(_translate_path(path))


def rename(old: str, new: str):
    """Rename a file or directory."""
    _real_os.rename(_translate_path(old), _translate_path(new))


def stat(path: str):
    """Get file status."""
    return _real_os.stat(_translate_path(path))


def statvfs(path: str):
    """Get filesystem statistics."""
    try:
        return _real_os.statvfs(_translate_path(path))
    except (OSError, AttributeError):
        # Return mock values if not available
        class MockStatvfs:
            f_bsize = 4096
            f_frsize = 4096
            f_blocks = 512
            f_bfree = 256
            f_bavail = 256
            f_files = 1000
            f_ffree = 500
            f_favail = 500
            f_flag = 0
            f_namemax = 255
        return MockStatvfs()


def sync():
    """Sync filesystem."""
    pass


def mount(filesystem, path: str, readonly: bool = False):
    """Mount a filesystem (stub)."""
    pass


def umount(path: str):
    """Unmount a filesystem (stub)."""
    pass


def dupterm(stream, index: int = 0):
    """Duplicate terminal (stub)."""
    pass


# File path helper
sep = _real_os.sep


def path_exists(path: str) -> bool:
    """Check if path exists."""
    return _real_os.path.exists(_translate_path(path))


def path_isfile(path: str) -> bool:
    """Check if path is a file."""
    return _real_os.path.isfile(_translate_path(path))


def path_isdir(path: str) -> bool:
    """Check if path is a directory."""
    return _real_os.path.isdir(_translate_path(path))


# Allow `open` with translated paths
def open_file(path: str, mode: str = "r"):
    """Open a file with path translation."""
    return open(_translate_path(path), mode)
