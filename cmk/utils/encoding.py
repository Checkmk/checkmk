#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This module provides some bytes-unicode encoding functions"""

from typing import (  # pylint: disable=unused-import
    AnyStr, Text, Optional,
)
import six


def convert_to_unicode(
    value,
    encoding=None,
    std_encoding="utf-8",
    fallback_encoding="latin-1",
    on_error=None,
):
    # type: (AnyStr, Optional[str], str, str, Optional[Text]) -> Text
    if isinstance(value, six.text_type):
        return value

    if encoding:
        return value.decode(encoding)

    try:
        return value.decode(std_encoding)
    except UnicodeDecodeError:
        pass

    try:
        return value.decode(fallback_encoding)
    except UnicodeDecodeError:
        if on_error is None:
            raise
        return on_error


def ensure_unicode(value):
    # type: (AnyStr) -> Text
    if isinstance(value, six.text_type):
        return value
    return value.decode("utf-8")


def ensure_bytestr(value):
    # type: (AnyStr) -> bytes
    if isinstance(value, six.binary_type):
        return value
    return value.encode("utf-8")


def make_utf8(value):
    # type: (AnyStr) -> bytes
    if isinstance(value, six.text_type):
        return value.encode('utf-8')
    return value
