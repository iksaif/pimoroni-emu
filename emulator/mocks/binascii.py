"""MicroPython binascii shim — crc32/hexlify/unhexlify accept str or bytes."""

import binascii as _b


def crc32(data, value=0):
    if isinstance(data, str):
        data = data.encode()
    return _b.crc32(data, value)


def hexlify(data, sep=None):
    if isinstance(data, str):
        data = data.encode()
    if sep is not None:
        return _b.hexlify(data, sep)
    return _b.hexlify(data)


def unhexlify(data):
    return _b.unhexlify(data)


def a2b_base64(data):
    return _b.a2b_base64(data)


def b2a_base64(data):
    return _b.b2a_base64(data)
