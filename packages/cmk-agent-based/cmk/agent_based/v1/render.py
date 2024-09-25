#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The "render" namespace adds functions to render values in a human readable way.

All of the render functions take a single numerical value as an argument, and return
a string.
"""

import math as _math
import time as _time
from collections.abc import Iterable as _Iterable

_DATE_FORMAT = "%Y-%m-%d"

_TIME_UNITS = [
    ("years", 31536000),
    ("days", 86400),
    ("hours", 3600),
    ("minutes", 60),
    ("seconds", 1),
    ("milliseconds", 1e-3),
    ("microseconds", 1e-6),
    ("nanoseconds", 1e-9),
    ("picoseconds", 1e-12),
    ("femtoseconds", 1e-15),
    # and while we're at it:
    ("attoseconds", 1e-18),
    ("zeptoseconds", 1e-21),
    ("yoctoseconds", 1e-24),
]

# Karl Marx Gave The Proletariat Eleven Zeppelins, Yo!
_SIZE_PREFIXES_SI = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
_SIZE_PREFIXES_IEC = _SIZE_PREFIXES_SI[:]
_SIZE_PREFIXES_IEC[1] = "K"


def date(epoch: float | None) -> str:
    """Render seconds since epoch as date

    Example:
        >>> date(None)
        'never'
        >>> _ = date(1606721022)

        The latter will return something like '2020-11-30', depending on the time zone.

    """
    if epoch is None:
        return "never"
    return _time.strftime(_DATE_FORMAT, _time.localtime(float(epoch)))


def datetime(epoch: float | None) -> str:
    """Render seconds since epoch as date and time

    Example:
        >>> datetime(None)
        'never'
        >>> _ = datetime(1606721022)

        The latter will return something like '2020-11-30 07:23:42',
        depending on the time zone.

    """
    if epoch is None:
        return "never"
    return _time.strftime(f"{_DATE_FORMAT} %H:%M:%S", _time.localtime(float(epoch)))


def _gen_timespan_chunks(seconds: float, nchunks: int) -> _Iterable[str]:
    if seconds < 0:
        raise ValueError("Cannot render negative timespan")

    try:
        start = next(i for i, (_, v) in enumerate(_TIME_UNITS) if seconds >= v)
    except StopIteration:
        start = len(_TIME_UNITS) - 1

    for unit, scale in _TIME_UNITS[start : start + nchunks]:
        last_chunk = unit.endswith("seconds")
        value = round(seconds / scale) if last_chunk else int(seconds / scale)
        yield f"{value:.0f} {unit if value != 1 else unit[:-1]}"
        if last_chunk:
            break
        seconds %= scale


def timespan(seconds: float) -> str:
    """Render a time span in seconds

    unaware of leap-years...

    Example:
        >>> timespan(1606721)
        '18 days 14 hours'
        >>> timespan(0.0001)
        '100 microseconds'
        >>> timespan(24*60*60)
        '1 day 0 hours'
        >>> timespan(365*24*60*60)
        '1 year 0 days'
        >>> timespan(100*365*24*60*60)
        '100 years 0 days'

    """
    ts = " ".join(_gen_timespan_chunks(float(seconds), nchunks=2))
    if ts == f"0 {_TIME_UNITS[-1][0]}":
        ts = "0 seconds"
    return ts


def _digits_left(value: float) -> int:
    """Return the number of didgits left of the decimal point

    Example:
        >>> _digits_left(42.23)
        2

    """
    try:
        return max(int(_math.log10(abs(value)) + 1), 1)
    except ValueError:
        return 1


def _auto_scale(value: float, use_si_units: bool, add_bytes_prefix: bool = True) -> tuple[str, str]:
    if use_si_units:
        base = 1000.0
        size_prefixes = _SIZE_PREFIXES_SI
    else:
        base = 1024.0
        size_prefixes = _SIZE_PREFIXES_IEC

    try:
        log_value = int(_math.log(abs(value), base))
    except ValueError:
        log_value = 0

    exponent = min(max(log_value, 0), len(size_prefixes) - 1)
    unit = size_prefixes[exponent]
    if add_bytes_prefix:
        unit = (unit + ("B" if use_si_units else "iB")).lstrip("i")
    scaled_value = float(value) / base**exponent
    fmt = f"%.{max(3 - _digits_left(scaled_value), 0)}f"
    return fmt % scaled_value, unit


def frequency(hertz: float) -> str:
    """Render a frequency in hertz using an appropriate SI prefix

    Example:
        >>> frequency(1e10 / 3.)
        '3.33 GHz'
    """
    value_str, unit = _auto_scale(float(hertz), use_si_units=True, add_bytes_prefix=False)
    return f"{value_str} {unit}Hz"


def disksize(bytes_: float) -> str:
    """Render a disk size in bytes using an appropriate SI prefix

    Example:
      >>> disksize(1024)
      '1.02 kB'
    """
    value_str, unit = _auto_scale(float(bytes_), use_si_units=True)
    return f"{value_str if unit != 'B' else value_str.split('.')[0]} {unit}"


def bytes(bytes_: float) -> str:  # noqa: A001
    """Render a number of bytes using an appropriate IEC prefix

    Example:
      >>> bytes(1024**2)
      '1.00 MiB'
    """
    value_str, unit = _auto_scale(float(bytes_), use_si_units=False)
    return f"{value_str if unit != 'B' else value_str.split('.')[0]} {unit}"


def filesize(bytes_: float) -> str:
    """Render a file size in bytes

    Example:
      >>> filesize(12345678)
      '12,345,678 B'
    """
    val_str = f"{float(bytes_):.0f}"
    offset = len(val_str) % 3

    groups = [val_str[0:offset]] + [val_str[i : i + 3] for i in range(offset, len(val_str), 3)]
    return f"{','.join(groups).strip(',')} B"


def networkbandwidth(octets_per_sec: float) -> str:
    """Render network bandwidth using an appropriate SI prefix"""
    value_str, unit = _auto_scale(float(octets_per_sec) * 8, use_si_units=True)
    return f"{value_str} {unit}it/s"


def nicspeed(octets_per_sec: float) -> str:
    """Render NIC speed using an appropriate SI prefix

    Example:
        >>> nicspeed(1050)
        '8.4 kBit/s'

    """
    value_str, unit = _auto_scale(float(octets_per_sec) * 8, use_si_units=True)
    if "." in value_str:
        value_str = value_str.rstrip("0").rstrip(".")
    return f"{value_str} {unit}it/s"


def iobandwidth(bytes_: float) -> str:
    """Render IO-bandwith using an appropriate SI prefix

    Example:
        >>> iobandwidth(128)
        '128 B/s'

    """
    value_str, unit = _auto_scale(float(bytes_), use_si_units=True)
    return f"{value_str} {unit}/s"


def percent(percentage: float) -> str:
    """Render percentage

    Example:
        >>> percent(23.4203245)
        '23.42%'
        >>> percent(0.003)
        '<0.01%'
        >>> percent(-0.003)
        '-0.00%'

    """
    # There is another render.percent in cmk.utils. However, that deals extensively with
    # the rendering of small percentages (as is required for graphing applications)
    value = float(percentage)  # be nice

    if value == 0.0:
        return "0%"

    if 0.0 < value < 0.01:
        return "<0.01%"

    # this includes negative values!
    return f"{value:.2f}%"


__all__ = [
    "bytes",
    "date",
    "datetime",
    "disksize",
    "filesize",
    "frequency",
    "iobandwidth",
    "networkbandwidth",
    "nicspeed",
    "percent",
    "timespan",
]
