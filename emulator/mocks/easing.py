"""Mock implementation of the easing module for Blinky 2350.

Provides standard easing functions for animation.
All functions take x in [0, 1] and return eased value.
"""

import math


def linear(x):
    return x


# --- Sine ---

def ease_in_sine(x):
    return 1 - math.cos((x * math.pi) / 2)


def ease_out_sine(x):
    return math.sin((x * math.pi) / 2)


def ease_in_out_sine(x):
    return -(math.cos(math.pi * x) - 1) / 2


# --- Quad ---

def ease_in_quad(x):
    return x * x


def ease_out_quad(x):
    return 1 - (1 - x) * (1 - x)


def ease_in_out_quad(x):
    if x < 0.5:
        return 2 * x * x
    return 1 - (-2 * x + 2) ** 2 / 2


# --- Cubic ---

def ease_in_cubic(x):
    return x * x * x


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out_cubic(x):
    if x < 0.5:
        return 4 * x * x * x
    return 1 - (-2 * x + 2) ** 3 / 2


# --- Quart ---

def ease_in_quart(x):
    return x ** 4


def ease_out_quart(x):
    return 1 - (1 - x) ** 4


def ease_in_out_quart(x):
    if x < 0.5:
        return 8 * x ** 4
    return 1 - (-2 * x + 2) ** 4 / 2


# --- Quint ---

def ease_in_quint(x):
    return x ** 5


def ease_out_quint(x):
    return 1 - (1 - x) ** 5


def ease_in_out_quint(x):
    if x < 0.5:
        return 16 * x ** 5
    return 1 - (-2 * x + 2) ** 5 / 2


# --- Expo ---

def ease_in_expo(x):
    if x == 0:
        return 0
    return 2 ** (10 * x - 10)


def ease_out_expo(x):
    if x == 1:
        return 1
    return 1 - 2 ** (-10 * x)


def ease_in_out_expo(x):
    if x == 0:
        return 0
    if x == 1:
        return 1
    if x < 0.5:
        return 2 ** (20 * x - 10) / 2
    return (2 - 2 ** (-20 * x + 10)) / 2


# --- Circ ---

def ease_in_circ(x):
    return 1 - math.sqrt(1 - x * x)


def ease_out_circ(x):
    return math.sqrt(1 - (x - 1) ** 2)


def ease_in_out_circ(x):
    if x < 0.5:
        return (1 - math.sqrt(1 - (2 * x) ** 2)) / 2
    return (math.sqrt(1 - (-2 * x + 2) ** 2) + 1) / 2


# --- Back ---

_c1 = 1.70158
_c2 = _c1 * 1.525
_c3 = _c1 + 1


def ease_in_back(x):
    return _c3 * x * x * x - _c1 * x * x


def ease_out_back(x):
    return 1 + _c3 * (x - 1) ** 3 + _c1 * (x - 1) ** 2


def ease_in_out_back(x):
    if x < 0.5:
        return ((2 * x) ** 2 * ((_c2 + 1) * 2 * x - _c2)) / 2
    return ((2 * x - 2) ** 2 * ((_c2 + 1) * (x * 2 - 2) + _c2) + 2) / 2


# --- Elastic ---

_c4 = (2 * math.pi) / 3
_c5 = (2 * math.pi) / 4.5


def ease_in_elastic(x):
    if x == 0:
        return 0
    if x == 1:
        return 1
    return -(2 ** (10 * x - 10)) * math.sin((x * 10 - 10.75) * _c4)


def ease_out_elastic(x):
    if x == 0:
        return 0
    if x == 1:
        return 1
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * _c4) + 1


def ease_in_out_elastic(x):
    if x == 0:
        return 0
    if x == 1:
        return 1
    if x < 0.5:
        return -(2 ** (20 * x - 10) * math.sin((20 * x - 11.125) * _c5)) / 2
    return (2 ** (-20 * x + 10) * math.sin((20 * x - 11.125) * _c5)) / 2 + 1


# --- Bounce ---

def ease_out_bounce(x):
    n1 = 7.5625
    d1 = 2.75
    if x < 1 / d1:
        return n1 * x * x
    elif x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    elif x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    else:
        x -= 2.625 / d1
        return n1 * x * x + 0.984375


def ease_in_bounce(x):
    return 1 - ease_out_bounce(1 - x)


def ease_in_out_bounce(x):
    if x < 0.5:
        return (1 - ease_out_bounce(1 - 2 * x)) / 2
    return (1 + ease_out_bounce(2 * x - 1)) / 2
