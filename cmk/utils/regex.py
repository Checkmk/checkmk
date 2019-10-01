#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""This module wraps some regex handling functions used by Check_MK"""

import re
from typing import Dict, Pattern, Tuple  # pylint:disable=unused-import

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

g_compiled_regexes = {}  # type: Dict[Tuple[str, int], Pattern]


def regex(pattern, flags=0):
    # type: (str, int) -> Pattern
    """Compile regex or look it up in already compiled regexes.
    (compiling is a CPU consuming process. We cache compiled regexes)."""
    try:
        return g_compiled_regexes[(pattern, flags)]
    except KeyError:
        pass

    try:
        reg = re.compile(pattern, flags=flags)
    except Exception as e:
        raise MKGeneralException(_("Invalid regular expression '%s': %s") % (pattern, e))

    g_compiled_regexes[(pattern, flags)] = reg
    return reg


def is_regex(pattern):
    # type: (str) -> bool
    """Checks if a string contains characters that make it neccessary
    to use regular expression logic to handle it correctly"""
    for c in pattern:
        if c in '.?*+^$|[](){}\\':
            return True
    return False


def escape_regex_chars(match):
    # type: (str) -> str
    r = ""
    for c in match:
        if c in r"[]\().?{}|*^$+":
            r += "\\"
        r += c
    return r
