#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains functions that transform Python values into
text representations optimized for human beings - with optional localization.
The resulting strings are not ment to be parsed into values again later. They
are just for optical output purposes."""

import abc
import math
import time
from datetime import timedelta
from typing import final, Optional, Sequence, Type, Union

from cmk.utils.i18n import _
from cmk.utils.type_defs import Seconds

# .
#   .--Date/Time-----------------------------------------------------------.
#   |           ____        _          _______ _                           |
#   |          |  _ \  __ _| |_ ___   / /_   _(_)_ __ ___   ___            |
#   |          | | | |/ _` | __/ _ \ / /  | | | | '_ ` _ \ / _ \           |
#   |          | |_| | (_| | ||  __// /   | | | | | | | | |  __/           |
#   |          |____/ \__,_|\__\___/_/    |_| |_|_| |_| |_|\___|           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Renderer(abc.ABC):
    """base class for renderers"""


class SecondsRenderer(Renderer):
    @staticmethod
    def get_tuple(value: Seconds) -> tuple[int, int, int, int]:
        """return a (days, hours, minutes, seconds) tuple
        >>> SecondsRenderer.get_tuple(1)
        (0, 0, 0, 1)
        >>> SecondsRenderer.get_tuple(90061)
        (1, 1, 1, 1)
        """
        days, rest = divmod(value, 86400)
        hours, rest = divmod(rest, 3600)
        mins, secs = divmod(rest, 60)
        return days, hours, mins, secs

    @classmethod
    def detailed_str(cls, value: Seconds) -> str:
        """Convert seconds into a more readable string
        >>> SecondsRenderer.detailed_str(1)
        '1 seconds'
        >>> SecondsRenderer.detailed_str(3600)
        '1 hours'
        """
        days, hours, mins, secs = cls.get_tuple(value)

        return " ".join(
            [
                "%d %s" % (val, label)
                for val, label in [
                    (days, _("days")),
                    (hours, _("hours")),
                    (mins, _("minutes")),
                    (secs, _("seconds")),
                ]
                if val > 0
            ]
        )


# NOTE: strftime's format *must* be of type str, both in Python 2 and 3.
def date(timestamp: Optional[float]) -> str:
    return time.strftime(str(_("%Y-%m-%d")), time.localtime(timestamp))


def date_and_time(timestamp: Optional[float]) -> str:
    return "%s %s" % (date(timestamp), time_of_day(timestamp))


# NOTE: strftime's format *must* be of type str, both in Python 2 and 3.
def time_of_day(timestamp: Optional[float]) -> str:
    return time.strftime(str(_("%H:%M:%S")), time.localtime(timestamp))


def timespan(seconds: Union[float, int]) -> str:
    return str(timedelta(seconds=int(seconds)))


def time_since(timestamp: int) -> str:
    return timespan(time.time() - timestamp)


class Age:
    """Format time difference seconds into approximated human readable text"""

    def __init__(self, secs: float, precision: Optional[int] = None) -> None:
        super().__init__()
        self.__secs = secs
        self.__precision = precision

    def __str__(self) -> str:
        secs = self.__secs
        precision = self.__precision

        if secs < 0:
            return "-" + approx_age(-secs)
        if precision and secs < 10 ** ((-1) * precision):
            return fmt_number_with_precision(secs, unit=_("s"), precision=precision)
        if 0 < secs < 1:  # ms
            return physical_precision(secs, 3, _("s"))
        if secs < 10:
            return "%.2f %s" % (secs, _("s"))
        if secs < 60:
            return "%.1f %s" % (secs, _("s"))
        if secs < 240:
            return "%d %s" % (secs, _("s"))

        mins = int(secs / 60.0)
        if mins < 360:
            return "%d %s" % (mins, _("m"))

        hours = int(mins / 60.0)
        if hours < 48:
            return "%d %s" % (hours, _("h"))

        days = hours / 24.0
        if days < 6:
            return "%s %s" % (drop_dotzero(days, 1), _("d"))
        if days < 999:
            return "%.0f %s" % (days, _("d"))
        years = days / 365.0
        if years < 10:
            return "%.1f %s" % (years, _("y"))

        return "%.0f %s" % (years, _("y"))

    def __float__(self) -> float:
        return float(self.__secs)


# TODO: Make call sites use Age() directly?
def approx_age(secs: float) -> str:
    return "%s" % Age(secs)


#   .--Prefix & Scale------------------------------------------------------.
#   |     ____            __ _         ___     ____            _           |
#   |    |  _ \ _ __ ___ / _(_)_  __  ( _ )   / ___|  ___ __ _| | ___      |
#   |    | |_) | '__/ _ \ |_| \ \/ /  / _ \/\ \___ \ / __/ _` | |/ _ \     |
#   |    |  __/| | |  __/  _| |>  <  | (_>  <  ___) | (_| (_| | |  __/     |
#   |    |_|   |_|  \___|_| |_/_/\_\  \___/\/ |____/ \___\__,_|_|\___|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


class _ABCUnitPrefixes(abc.ABC):
    _BASE: int
    _PREFIXES: Sequence[str]

    @final
    @classmethod
    def scale_factor_and_prefix(cls, v: float) -> tuple[float, str]:
        prefix = cls._PREFIXES[-1]
        factor = cls._BASE
        for unit_prefix in cls._PREFIXES[:-1]:
            if abs(v) < factor:
                prefix = unit_prefix
                break
            factor *= cls._BASE
        return factor / cls._BASE, prefix


class SIUnitPrefixes(_ABCUnitPrefixes):
    """
    SI unit prefixes

    >>> SIUnitPrefixes.scale_factor_and_prefix(1)
    (1.0, '')
    >>> SIUnitPrefixes.scale_factor_and_prefix(1001.123)
    (1000.0, 'k')
    >>> SIUnitPrefixes.scale_factor_and_prefix(5_000_000_000)
    (1000000000.0, 'G')
    """

    _BASE = 1000
    _PREFIXES = ("", "k", "M", "G", "T", "P", "E", "Z", "Y")


class IECUnitPrefixes(_ABCUnitPrefixes):
    """
    IEC unit prefixes

    >>> IECUnitPrefixes.scale_factor_and_prefix(1)
    (1.0, '')
    >>> IECUnitPrefixes.scale_factor_and_prefix(1025)
    (1024.0, 'Ki')
    >>> IECUnitPrefixes.scale_factor_and_prefix(5_000_000_000)
    (1073741824.0, 'Gi')
    """

    _BASE = 1024
    _PREFIXES = ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi")


def drop_dotzero(v: float, digits: int = 2) -> str:
    """Renders a number as a floating point number and drops useless
    zeroes at the end of the fraction

    >>> drop_dotzero(45.1)
    '45.1'
    >>> drop_dotzero(45.0)
    '45'
    >>> drop_dotzero(45.111, 1)
    '45.1'
    >>> drop_dotzero(45.999, 1)
    '46'
    """
    t = "%.*f" % (digits, v)
    if "." in t:
        return t.rstrip("0").rstrip(".")
    return t


def fmt_number_with_precision(
    v: float,
    *,
    precision: int = 2,
    drop_zeroes: bool = False,
    unit_prefix_type: Type[_ABCUnitPrefixes] = SIUnitPrefixes,
    unit: str = "",
    zero_non_decimal: bool = False,
) -> str:
    factor, prefix = unit_prefix_type.scale_factor_and_prefix(v)
    value = float(v) / factor
    if zero_non_decimal and value == 0:
        return "0 %s" % prefix + unit
    number = drop_dotzero(value, precision) if drop_zeroes else "%.*f" % (precision, value)
    return "%s %s" % (number, prefix + unit)


# .
#   .--Bits/Bytes----------------------------------------------------------.
#   |            ____  _ _          ______        _                        |
#   |           | __ )(_) |_ ___   / / __ ) _   _| |_ ___  ___             |
#   |           |  _ \| | __/ __| / /|  _ \| | | | __/ _ \/ __|            |
#   |           | |_) | | |_\__ \/ / | |_) | |_| | ||  __/\__ \            |
#   |           |____/|_|\__|___/_/  |____/ \__, |\__\___||___/            |
#   |                                       |___/                          |
#   '----------------------------------------------------------------------'


def fmt_bytes(
    b: int,
    *,
    unit_prefix_type: Type[_ABCUnitPrefixes] = IECUnitPrefixes,
    precision: int = 2,
    unit="B",
) -> str:
    """Formats byte values to be used in texts for humans.

    Takes bytes as integer and returns a string which represents the bytes in a
    more human readable form scaled to TB/GB/MB/KB. The unit parameter simply
    changes the returned string, but does not interfere with any calculations."""
    return fmt_number_with_precision(
        b,
        unit_prefix_type=unit_prefix_type,
        precision=precision,
        unit=unit,
    )


# Precise size of a file - separated decimal separator
# 1234 -> "1234"
# 12345 => "12,345"
def filesize(size: float) -> str:
    dec_sep = ","
    if size < 10000:
        return str(size)
    if size < 1000000:
        return str(size)[:-3] + dec_sep + str(size)[-3:]
    if size < 1000000000:
        return str(size)[:-6] + dec_sep + str(size)[-6:-3] + dec_sep + str(size)[-3:]

    return (
        str(size)[:-9]
        + dec_sep
        + str(size)[-9:-6]
        + dec_sep
        + str(size)[-6:-3]
        + dec_sep
        + str(size)[-3:]
    )


def fmt_nic_speed(speed: str | int) -> str:
    """Format network speed (bit/s) for humans."""
    try:
        speedi = int(speed)
    except ValueError:
        return str(speed)

    return fmt_number_with_precision(
        speedi, unit_prefix_type=SIUnitPrefixes, precision=2, unit="bit/s", drop_zeroes=True
    )


# .
#   .--Misc.Numbers--------------------------------------------------------.
#   |    __  __ _            _   _                 _                       |
#   |   |  \/  (_)___  ___  | \ | |_   _ _ __ ___ | |__   ___ _ __ ___     |
#   |   | |\/| | / __|/ __| |  \| | | | | '_ ` _ \| '_ \ / _ \ '__/ __|    |
#   |   | |  | | \__ \ (__ _| |\  | |_| | | | | | | |_) |  __/ |  \__ \    |
#   |   |_|  |_|_|___/\___(_)_| \_|\__,_|_| |_| |_|_.__/ \___|_|  |___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def percent(perc: float, scientific_notation: bool = False) -> str:
    """Renders a given number as percentage string"""
    # 0 and 0.0 is a special case
    if perc == 0:
        return "0%"

    # 1000 < oo
    if scientific_notation and abs(perc) >= 100000:
        result = scientific(perc, 1)
    # 100 < 1000 < oo
    elif abs(perc) >= 100:
        result = "%d" % perc
    # 0.0 < 0.001
    elif 0.0 < abs(perc) < 0.01:
        result = "%.7f" % round(perc, -int(math.floor(math.log10(abs(perc)))))
        # for super small numbers < 0.0000001%, just return 0%
        if float(result) == 0:
            return "0%"
        if scientific_notation and perc < 0.0001:
            result = scientific(perc, 1)
        else:
            result = result.rstrip("0")
    # 0.001 < 100
    else:
        result = drop_dotzero(perc, 2)

    # add .0 to all integers < 100
    if float(result).is_integer() and float(result) < 100:
        result += ".0"

    return result + "%"


def scientific(v: float, precision: int = 3) -> str:
    """Renders a given number in scientific notation (E-notation)"""
    if v == 0:
        return "0"
    if v < 0:
        return "-" + scientific(v * -1, precision)

    mantissa, exponent = _frexp10(float(v))
    # Render small numbers without exponent
    if -3 <= exponent <= 4:
        return "%.*f" % (min(precision, max(0, precision - exponent)), v)

    return "%.*fe%+d" % (precision, mantissa, exponent)


# Render a physical value with a precision of p
# digits. Use K (kilo), M (mega), m (milli), µ (micro)
# p is the number of non-zero digits - not the number of
# decimal places.
# Examples for p = 3:
# a: 0.0002234   b: 4,500,000  c: 137.56
# Result:
# a: 223 µ       b: 4.50 M     c: 138
#
# Note if the type of v is integer, then the precision cut
# down to the precision of the actual number
def physical_precision(v: float, precision: int, unit_symbol: str) -> str:
    if v < 0:
        return "-" + physical_precision(-v, precision, unit_symbol)

    scale_symbol, places_after_comma, scale_factor = calculate_physical_precision(v, precision)

    scaled_value = float(v) / scale_factor
    return "%.*f %s%s" % (places_after_comma, scaled_value, scale_symbol, unit_symbol)


def calculate_physical_precision(v: float, precision: int) -> tuple[str, int, int]:
    if v == 0:
        return "", precision - 1, 1

    # Splitup in mantissa (digits) an exponent to the power of 10
    # -> a: (2.23399998, -2)  b: (4.5, 6)    c: (1.3756, 2)
    _mantissa, exponent = _frexp10(float(v))

    if isinstance(v, int):
        precision = min(precision, exponent + 1)

    # Choose a power where no artifical zero (due to rounding) needs to be
    # placed left of the decimal point.
    scale_symbols = {
        -5: "f",
        -4: "p",
        -3: "n",
        -2: "µ",
        -1: "m",
        0: "",
        1: "k",
        2: "M",
        3: "G",
        4: "T",
        5: "P",
    }
    scale = 0

    while exponent < 0 and scale > -5:
        scale -= 1
        exponent += 3

    # scale, exponent = divmod(exponent, 3)
    places_before_comma = exponent + 1
    places_after_comma = precision - places_before_comma
    while places_after_comma < 0 and scale < 5:
        scale += 1
        exponent -= 3
        places_before_comma = exponent + 1
        places_after_comma = precision - places_before_comma

    return scale_symbols[scale], places_after_comma, 1000**scale


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _frexp10(x: float) -> tuple[float, int]:
    return _frexpb(x, 10)


def _frexpb(x: float, base: int) -> tuple[float, int]:
    exp = int(math.log(x, base))
    mantissa = x / base**exp
    if mantissa < 1:
        mantissa *= base
        exp -= 1
    return mantissa, exp
