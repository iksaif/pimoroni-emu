"""Mock implementation of MicroPython's socket module.

Uses real sockets so that network requests pass through to the host.
"""

import socket as _socket
from typing import Optional, Tuple
from emulator import get_state


# Constants
AF_INET = _socket.AF_INET
AF_INET6 = _socket.AF_INET6
SOCK_STREAM = _socket.SOCK_STREAM
SOCK_DGRAM = _socket.SOCK_DGRAM
SOCK_RAW = _socket.SOCK_RAW
SOL_SOCKET = _socket.SOL_SOCKET
SO_REUSEADDR = _socket.SO_REUSEADDR
IPPROTO_TCP = _socket.IPPROTO_TCP
IPPROTO_UDP = _socket.IPPROTO_UDP

# Default timeout used by http.client / urllib
_GLOBAL_DEFAULT_TIMEOUT = _socket._GLOBAL_DEFAULT_TIMEOUT


class socket:
    """Socket wrapper that can use real or mocked sockets."""

    def __init__(self, af: int = AF_INET, socktype: int = SOCK_STREAM, proto: int = 0):
        self._af = af
        self._type = socktype
        self._proto = proto
        self._connected = False
        self._blocking = True
        self._timeout = None
        self._real_socket = _socket.socket(af, socktype, proto)

        if get_state().get("trace"):
            print(f"[socket] Created af={af} type={socktype}")

    def connect(self, address: Tuple[str, int]):
        """Connect to remote address."""
        if get_state().get("trace"):
            print(f"[socket] Connect to {address}")

        if self._real_socket:
            self._real_socket.connect(address)
        self._connected = True

    def bind(self, address: Tuple[str, int]):
        """Bind to local address."""
        if get_state().get("trace"):
            print(f"[socket] Bind to {address}")

        if self._real_socket:
            self._real_socket.bind(address)

    def listen(self, backlog: int = 1):
        """Listen for connections."""
        if self._real_socket:
            self._real_socket.listen(backlog)

    def accept(self) -> Tuple["socket", Tuple[str, int]]:
        """Accept incoming connection."""
        if self._real_socket:
            conn, addr = self._real_socket.accept()
            wrapper = socket(self._af, self._type, self._proto)
            wrapper._real_socket = conn
            wrapper._connected = True
            return wrapper, addr
        raise OSError("No real socket available")

    def send(self, data: bytes) -> int:
        """Send data."""
        if get_state().get("trace"):
            print(f"[socket] Send {len(data)} bytes")

        if self._real_socket:
            return self._real_socket.send(data)
        return len(data)

    def sendall(self, data: bytes):
        """Send all data."""
        if self._real_socket:
            self._real_socket.sendall(data)
        elif get_state().get("trace"):
            print(f"[socket] Sendall {len(data)} bytes (mock)")

    def sendto(self, data: bytes, address: Tuple[str, int]) -> int:
        """Send data to address (UDP)."""
        if self._real_socket:
            return self._real_socket.sendto(data, address)
        return len(data)

    def recv(self, bufsize: int) -> bytes:
        """Receive data."""
        if self._real_socket:
            return self._real_socket.recv(bufsize)
        # Mock: return empty for non-blocking, block forever for blocking
        return b""

    def recvfrom(self, bufsize: int) -> Tuple[bytes, Tuple[str, int]]:
        """Receive data with sender address (UDP)."""
        if self._real_socket:
            return self._real_socket.recvfrom(bufsize)
        return b"", ("0.0.0.0", 0)

    def read(self, size: int = -1) -> bytes:
        """Read data (file-like interface)."""
        if size < 0:
            size = 4096
        return self.recv(size)

    def readline(self) -> bytes:
        """Read a line."""
        result = bytearray()
        while True:
            c = self.recv(1)
            if not c:
                break
            result.extend(c)
            if c == b"\n":
                break
        return bytes(result)

    def write(self, data: bytes) -> int:
        """Write data (file-like interface)."""
        return self.send(data)

    def close(self):
        """Close socket."""
        if self._real_socket:
            self._real_socket.close()
            self._real_socket = None
        self._connected = False
        if get_state().get("trace"):
            print("[socket] Closed")

    def setblocking(self, flag: bool):
        """Set blocking mode."""
        self._blocking = flag
        if self._real_socket:
            self._real_socket.setblocking(flag)

    def settimeout(self, timeout: Optional[float]):
        """Set timeout."""
        self._timeout = timeout
        if self._real_socket:
            self._real_socket.settimeout(timeout)

    def setsockopt(self, level: int, optname: int, value):
        """Set socket option."""
        if self._real_socket:
            self._real_socket.setsockopt(level, optname, value)

    def makefile(self, mode: str = "rb", buffering: int = 0):
        """Create file-like wrapper."""
        if self._real_socket:
            return self._real_socket.makefile(mode, buffering)
        return self


def getaddrinfo(
    host: str,
    port: int,
    af: int = 0,
    socktype: int = 0,
    proto: int = 0,
    flags: int = 0
) -> list:
    """Get address info for host."""
    if get_state().get("trace"):
        print(f"[socket] getaddrinfo({host}, {port})")

    return _socket.getaddrinfo(host, port, af, socktype, proto, flags)
