#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains functions that transform Python values into
text representations optimized for human beings - with optional localization.
The resulting strings are not ment to be parsed into values again later. They
are just for optical output purposes."""

# THIS IS STILL EXPERIMENTAL

import time
import math
from datetime import timedelta
from typing import Optional, Tuple, Union

from cmk.utils.i18n import _

#.
#   .--Date/Time-----------------------------------------------------------.
#   |           ____        _          _______ _                           |
#   |          |  _ \  __ _| |_ ___   / /_   _(_)_ __ ___   ___            |
#   |          | | | |/ _` | __/ _ \ / /  | | | | '_ ` _ \ / _ \           |
#   |          | |_| | (_| | ||  __// /   | | | | | | | | |  __/           |
#   |          |____/ \__,_|\__\___/_/    |_| |_|_| |_| |_|\___|           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


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
    def __init__(self, secs: float) -> None:
        super(Age, self).__init__()
        self.__secs = secs

    def __str__(self) -> str:
        secs = self.__secs

        if secs < 0:
            return "-" + approx_age(-secs)
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
            d = ("%.1f" % days).rstrip("0").rstrip(".")
            return "%s %s" % (d, _("d"))
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


#.
#   .--Bits/Bytes----------------------------------------------------------.
#   |            ____  _ _          ______        _                        |
#   |           | __ )(_) |_ ___   / / __ ) _   _| |_ ___  ___             |
#   |           |  _ \| | __/ __| / /|  _ \| | | | __/ _ \/ __|            |
#   |           | |_) | | |_\__ \/ / | |_) | |_| | ||  __/\__ \            |
#   |           |____/|_|\__|___/_/  |____/ \__, |\__\___||___/            |
#   |                                       |___/                          |
#   '----------------------------------------------------------------------'


def scale_factor_prefix(
    value: float, base: float,
    prefixes: Tuple[str, ...] = ('', 'k', 'M', 'G', 'T', 'P')) -> Tuple[float, str]:
    base = float(base)

    prefix = prefixes[-1]
    factor = base
    for unit_prefix in prefixes[:-1]:
        if abs(value) < factor:
            prefix = unit_prefix
            break
        factor *= base
    return factor / base, prefix  # fixed: true-division


def drop_dotzero(v: float, digits: int = 2) -> str:
    """Renders a number as a floating point number and drops useless
    zeroes at the end of the fraction

    45.1 -> "45.1"
    45.0 -> "45"
    """
    t = '%.*f' % (digits, v)
    if "." in t:
        return t.rstrip("0").rstrip(".")
    return t


def fmt_number_with_precision(v: float,
                              base: float = 1000.0,
                              precision: int = 2,
                              drop_zeroes: bool = False,
                              unit: str = "") -> str:
    factor, prefix = scale_factor_prefix(v, base)
    value = float(v) / factor
    number = drop_dotzero(value, precision) if drop_zeroes else '%.*f' % (precision, value)
    return '%s %s' % (number, prefix + unit)


def fmt_bytes(b: int, base: float = 1024.0, precision: int = 2, unit: str = "B") -> str:
    """Formats byte values to be used in texts for humans.

    Takes bytes as integer and returns a string which represents the bytes in a
    more human readable form scaled to TB/GB/MB/KB. The unit parameter simply
    changes the returned string, but does not interfere with any calculations."""
    return fmt_number_with_precision(b, base=base, precision=precision, unit=unit)


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

    return str(size)[:-9] + dec_sep + str(size)[-9:-6] + dec_sep + str(size)[-6:-3] + dec_sep + str(
        size)[-3:]


#.
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
    # 0 / 0.0 -> 0%
    # 9.0e-05 -> 0.00009%
    # 0.00009 -> 0.00009%
    # 0.00103 -> 0.001%
    # 0.0019  -> 0.002%
    # 0.129   -> 0.13%
    # 8.25752 -> 8.26%
    # 8       -> 8.0%
    # 80      -> 80.0%
    # 100.123 -> 100%
    # 200.123 -> 200%
    # 1234567 -> 1234567%
    #
    # with scientific_notation:
    # 0.00009 -> 9.0e-05%
    # 0.00019 -> 0.0002%
    # 12345 -> 12345%
    # 1234567 -> 1.2e+06%

    # 0 and 0.0 is a special case
    if perc == 0:
        return "0%"

    # 1000 < oo
    if abs(perc) > 999.5:
        if scientific_notation and abs(perc) >= 100000:
            result = "%1.e" % perc
        else:
            # TODO: in python3 change to >= 999.5
            # the way python rounds x.5 changed between py2 and py3
            result = "%d" % perc
    # 100 < 1000
    elif abs(perc) >= 100:
        result = "%d" % perc
    # 0.0 < 0.001
    elif 0.0 < abs(perc) < 0.01:
        result = "%.7f" % round(perc, -int(math.floor(math.log10(abs(perc)))))
        # for super small numbers < 0.0000001%, just return 0%
        if float(result) == 0:
            return "0%"
        if scientific_notation and perc < 0.0001:
            result = "%1.e" % float(result)
        else:
            result = result.rstrip("0")
    # 0.001 < 100
    else:
        result = "%.2f" % perc
        result = result.rstrip("0").rstrip(".")

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
        return "%%.%df" % max(0, precision - exponent) % v

    return "%%.%dfe%%d" % precision % (mantissa, exponent)


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
    return (u"%%.%df %%s%%s" % places_after_comma) % (scaled_value, scale_symbol, unit_symbol)


def calculate_physical_precision(v: float, precision: int) -> Tuple[str, int, int]:
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
        -2: u"µ",
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


def fmt_nic_speed(speed: str) -> str:
    """Format network speed (bit/s) for humans."""
    try:
        speedi = int(speed)
    except ValueError:
        return speed

    return fmt_number_with_precision(speedi,
                                     base=1000.0,
                                     precision=2,
                                     unit="bit/s",
                                     drop_zeroes=True)


#.
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _frexp10(x: float) -> Tuple[float, int]:
    return _frexpb(x, 10)


def _frexpb(x: float, base: int) -> Tuple[float, int]:
    exp = int(math.log(x, base))
    mantissa = x / base**exp
    if mantissa < 1:
        mantissa *= base
        exp -= 1
    return mantissa, exp
