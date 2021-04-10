#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module wraps some regex handling functions used by Check_MK"""

import re
from typing import Any, AnyStr, Dict, Pattern, Tuple

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

g_compiled_regexes: Dict[Tuple[Any, int], Pattern] = {}

REGEX_HOST_NAME_CHARS = r'-0-9a-zA-Z_.'
REGEX_HOST_NAME = r'^[%s]+$' % REGEX_HOST_NAME_CHARS


def regex(pattern: AnyStr, flags: int = 0) -> Pattern[AnyStr]:
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


def is_regex(pattern: str) -> bool:
    """Checks if a string contains characters that make it neccessary
    to use regular expression logic to handle it correctly"""
    for c in pattern:
        if c in '.?*+^$|[](){}\\':
            return True
    return False


def escape_regex_chars(match: str) -> str:
    r = ""
    for c in match:
        if c in r"[]\().?{}|*^$+":
            r += "\\"
        r += c
    return r


def unescape(pattern: str) -> str:
    r"""Reverse of re.escape()

    >>> from cmk.utils.regex import unescape
    >>> unescape(re.escape(r"a b c"))
    'a b c'
    >>> unescape(re.escape(r"http://abc.de/"))
    'http://abc.de/'
    >>> unescape(re.escape(r"\\u\n\c"))
    '\\\\u\\n\\c'
    >>> unescape(re.escape(r"ä b .*(C)"))
    'ä b .*(C)'
    """
    return re.sub(r'\\(.)', r'\1', pattern)
