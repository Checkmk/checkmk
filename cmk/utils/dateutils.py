#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.ccc.i18n import _

Weekday = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def weekday_name(day_num: int) -> str:
    """Returns the human readable day name of a given weekday number (starting with 0 at Monday)"""
    return weekdays()[day_num]


def weekday_ids() -> list[Weekday]:
    """Returns a list of the internal week day names"""
    return [d[0] for d in weekdays_by_name()]


def weekdays() -> dict[int, str]:
    """Returns a map of weekday number (starting with 0 at Monday) to the human readable day name"""
    return {
        0: _("Monday"),
        1: _("Tuesday"),
        2: _("Wednesday"),
        3: _("Thursday"),
        4: _("Friday"),
        5: _("Saturday"),
        6: _("Sunday"),
    }


def weekdays_by_name() -> list[tuple[Weekday, str]]:
    """Returns a list of two element tuples containing the weekday ID and the human readable day name"""
    return [
        ("monday", _("Monday")),
        ("tuesday", _("Tuesday")),
        ("wednesday", _("Wednesday")),
        ("thursday", _("Thursday")),
        ("friday", _("Friday")),
        ("saturday", _("Saturday")),
        ("sunday", _("Sunday")),
    ]


def month_name(month_num: int) -> str:
    """Returns the human readable month name of a given month number
    (starting with 0 = January)"""
    return [
        _("January"),
        _("February"),
        _("March"),
        _("April"),
        _("May"),
        _("June"),
        _("July"),
        _("August"),
        _("September"),
        _("October"),
        _("November"),
        _("December"),
    ][month_num]
