#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render functions for check development

These are meant to be exposed in the API
"""
from typing import Iterable, Optional, Tuple
import math
import time

_DATE_FORMAT = "%b %d %Y"

_TIME_UNITS = [
    ('years', 31536000),
    ('days', 86400),
    ('hours', 3600),
    ('minutes', 60),
    ('seconds', 1),
    ('milliseconds', 1e-3),
    ('microseconds', 1e-6),
    ('nanoseconds', 1e-9),
    ('picoseconds', 1e-12),
    ('femtoseconds', 1e-15),
    # and while we're at it:
    ('attoseconds', 1e-18),
    ('zeptoseconds', 1e-21),
    ('yoctoseconds', 1e-24),
]

# Karl Marx Gave The Proletariat Eleven Zeppelins, Yo!
_SIZE_PREFIXES = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']


def date(epoch: Optional[float]) -> str:
    """Render seconds since epoch as date

    In case None is given it returns "never".
    """
    if epoch is None:
        return "never"
    return time.strftime(_DATE_FORMAT, time.localtime(float(epoch)))


def datetime(epoch: Optional[float]) -> str:
    """Render seconds since epoch as date and time

    In case None is given it returns "never".
    """
    if epoch is None:
        return "never"
    return time.strftime("%s %%H:%%M:%%S" % _DATE_FORMAT, time.localtime(float(epoch)))


def _gen_timespan_chunks(seconds: float, nchunks: int) -> Iterable[str]:
    if seconds < 0:
        raise ValueError("Cannot render negative timespan")

    try:
        start = next(i for i, (_, v) in enumerate(_TIME_UNITS) if seconds >= v)
    except StopIteration:
        start = len(_TIME_UNITS) - 1

    for unit, scale in _TIME_UNITS[start:start + nchunks]:
        value = int(seconds / scale)
        yield "%.0f %s" % (value, unit if value != 1 else unit[:-1])
        if unit.endswith("seconds"):
            break
        seconds %= scale


def timespan(seconds: float) -> str:
    """Render a time span in seconds
    """
    ts = " ".join(_gen_timespan_chunks(float(seconds), nchunks=2))
    if ts == "0 %s" % _TIME_UNITS[-1][0]:
        ts = "0 seconds"
    return ts


def _digits_left(value: float) -> int:
    """Return the number of didgits left of the decimal point"""
    try:
        return max(int(math.log10(value) + 1), 1)
    except ValueError:  # value is exactly zero
        if value < 0:
            raise
        return 1


def _auto_scale(value: float, use_si_units: bool) -> Tuple[str, str]:
    base = 1000 if use_si_units else 1024
    try:
        exponent = min(max(int(math.log(value, base)), 0), len(_SIZE_PREFIXES) - 1)
    except ValueError:
        if value < 0:
            raise
        exponent = 0
    unit = (_SIZE_PREFIXES[exponent] + ("B" if use_si_units else "iB")).lstrip('i')
    scaled_value = float(value) / base**exponent
    fmt = "%%.%df" % max(3 - _digits_left(scaled_value), 0)
    return fmt % scaled_value, unit


def disksize(bytes_: float) -> str:
    """Render a disk size in bytes using an appropriate SI prefix

    Example:
      >>> disksize(1024)
      "1.02 KB"
    """
    value_str, unit = _auto_scale(float(bytes_), use_si_units=True)
    return "%s %s" % (value_str if unit != "B" else value_str.split('.')[0], unit)


def bytes(bytes_: float) -> str:  # pylint: disable=redefined-builtin
    """Render a number of bytes using an appropriate IEC prefix

    Example:
      >>> bytes(1024**2)
      "2.00 MiB"
    """
    value_str, unit = _auto_scale(float(bytes_), use_si_units=False)
    return "%s %s" % (value_str if unit != "B" else value_str.split('.')[0], unit)


def filesize(bytes_: float) -> str:
    """Render a file size in bytes

    Example:
      >>> filesize(12345678)
      "12,345,678"
    """
    val_str = "%.0f" % float(bytes_)
    if len(val_str) <= 3:
        return "%s B" % val_str

    offset = len(val_str) % 3
    groups = [val_str[0:offset]] + [val_str[i:i + 3] for i in range(offset, len(val_str), 3)]
    return "%s B" % ','.join(groups)


def networkbandwidth(octets_per_sec: float) -> str:
    """Render network bandwidth using an appropriate SI prefix"""
    return "%s %sit/s" % _auto_scale(float(octets_per_sec) * 8, use_si_units=True)


def nicspeed(octets_per_sec: float) -> str:
    """Render NIC speed using an appropriate SI prefix"""
    value_str, unit = _auto_scale(float(octets_per_sec) * 8, use_si_units=True)
    if '.' in value_str:
        value_str = value_str.rstrip("0").rstrip(".")
    return "%s %sit/s" % (value_str, unit)


def iobandwidth(bytes_: float) -> str:
    """Render IO-bandwith using an appropriate SI prefix"""
    return "%s %s/s" % _auto_scale(float(bytes_), use_si_units=True)


def percent(percentage: float) -> str:
    """Render percentage"""
    # There is another render.percent in cmk.utils. However, that deals extensively with
    # the rendering of small percentages (as is required for graphing applications)
    # However, we assume that if a percentage value is smaller that 0.01%, we can display
    # it as 0.00%.
    # If this is the case regularly, you probably want to display something different,
    # "parts per million" for instance.
    # Also, this way this module is completely stand alone.
    value = float(percentage)  # be nice
    if not value:
        return "0%"
    digits_int = _digits_left(value)
    digits_frac = max(3 - digits_int, 0)
    if 99 < value < 100:  # be more precise in this case
        digits_frac = _digits_left(1. / (100.0 - value))
    fmt = "%%.%df%%%%" % digits_frac
    return fmt % value
