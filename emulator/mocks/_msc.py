"""Stub `_msc` module for the emulator.

On real hardware, importing `_msc` enables USB Mass Storage mode
(exposes the device's flash to the host PC). In the emulator there's
no USB to manipulate, so this is a no-op stub — apps that
`import _msc` to enter MSC just keep running.
"""


def enable():
    pass


def disable():
    pass


# Apps do `import _msc.py # noqa F401` (a quirk of MicroPython treating
# bare filenames as importable). CPython parses that as `import _msc.py`
# — which is `import x.y` syntax requiring `_msc` to be a package. We
# fake packagehood by setting __path__, then expose a `py` submodule via
# sys.modules so the import resolves.
import sys as _sys
__path__ = []  # noqa: PYL — declares this module as a namespace package
py = _sys.modules[__name__]  # `_msc.py` resolves to ourselves
_sys.modules.setdefault("_msc.py", _sys.modules[__name__])
