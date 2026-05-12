"""Network probe abstraction.

Same API in three modes:
  * real    — TCP connect to a host:port as a latency proxy. Works on
              real Pico W hardware (no ICMP needed) and in the emulator
              (the socket mock passes through to host sockets).
  * sim     — fully simulated values, driven by --network-profile.
  * host    — like real but exposes the host's actual RSSI when the
              emulator can read it (configured via --network-profile host).

The mode is selected from the EMU_NETWORK_PROFILE env var the emulator
sets. On real hardware that variable is absent, so we default to real.
"""

import os
import random
import time


try:
    import socket as _socket
except ImportError:                    # MicroPython: same module name
    import usocket as _socket          # type: ignore


# ─── Mode detection ────────────────────────────────────────────────────


def get_profile():
    """The active network profile string ('real', 'host', 'healthy', ...)."""
    return os.environ.get("EMU_NETWORK_PROFILE", "real")


def _profile_sim_params():
    """Return (lat_mean_ms, jitter_ms, loss_pct, dns_mean_ms, can_resolve)."""
    p = get_profile()
    if p == "healthy":
        return 18.0, 1.5, 0.0, 14.0, True
    if p == "degraded":
        return 187.0, 38.0, 12.0, 410.0, True
    if p == "down":
        return None, None, 100.0, None, False
    return None  # not a simulated profile


# ─── Real-network probes ───────────────────────────────────────────────


def _tcp_ping(host, port=53, timeout=1.0):
    """Measure TCP connect time in ms. Returns None on failure."""
    try:
        addrs = _socket.getaddrinfo(host, port)
        if not addrs:
            return None
        family, sock_type, proto, _, sockaddr = addrs[0]
        s = _socket.socket(family, _socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            t0 = time.time()
            s.connect(sockaddr)
            return (time.time() - t0) * 1000.0
        finally:
            try:
                s.close()
            except Exception:
                pass
    except (OSError, _socket.gaierror, Exception):
        return None


def _real_dns_ms(name="cloudflare.com"):
    """Measure DNS resolution time in ms. Returns None on failure."""
    try:
        t0 = time.time()
        _socket.getaddrinfo(name, 0)
        return (time.time() - t0) * 1000.0
    except Exception:
        return None


# ─── Public probe API ──────────────────────────────────────────────────


def probe(target, port=53, dns_name=None):
    """Return a metrics dict for a target.

    Keys: latency_ms, dns_ms (only when dns_name is given), ok (bool).
    """
    sim = _profile_sim_params()
    if sim is not None:
        lat_mean, jitter, loss, dns_mean, can_resolve = sim
        # Loss roll
        if random.uniform(0, 100) < loss:
            return {"latency_ms": None, "dns_ms": None, "ok": False}
        lat = lat_mean + random.uniform(-jitter, jitter) if lat_mean else None
        dns = (dns_mean + random.uniform(-jitter, jitter)) if dns_name and dns_mean else None
        if not can_resolve and dns_name:
            dns = None
        return {"latency_ms": lat, "dns_ms": dns, "ok": lat is not None}

    lat = _tcp_ping(target, port=port)
    dns = _real_dns_ms(dns_name) if dns_name else None
    return {"latency_ms": lat, "dns_ms": dns, "ok": lat is not None}


def rssi_dbm():
    """Current WiFi RSSI in dBm. Routes through `network.WLAN` so the host
    or simulated profile applies."""
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        return wlan.status("rssi")
    except Exception:
        return -60


def is_connected():
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        return bool(wlan.isconnected())
    except Exception:
        return True  # assume yes — let probes fail naturally if not
