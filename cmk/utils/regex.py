#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module wraps some regex handling functions used by Check_MK"""


import contextlib
import re
from typing import Final

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

g_compiled_regexes: dict[tuple[str, int], re.Pattern[str]] = {}

REGEX_HOST_NAME_CHARS: Final = r"-0-9a-zA-Z_."
REGEX_HOST_NAME: Final = f"^[{REGEX_HOST_NAME_CHARS}]{{,253}}$"

REGEX_GENERIC_IDENTIFIER_CHARS: Final = r"-0-9a-zA-Z_."
REGEX_GENERIC_IDENTIFIER: Final = f"^[{REGEX_GENERIC_IDENTIFIER_CHARS}]+$"

# Start with a char, and no dots
REGEX_ID: Final = r"^[^\d\W][-\w]*$"

# URL CHARS
# See https://www.ietf.org/rfc/rfc3986.txt
_URL_UNRESERVED_CHARS: Final = re.escape("-.~")
_URL_GEN_DELIMS: Final = re.escape(":/?#[]@")
_URL_SUB_DELIMS: Final = re.escape("!$&()*+,;=")  # Leaving out "'"
# The space character should be encoded but it often isn't, so we allow it
URL_CHAR_REGEX_CHARS: Final = r" \w%" + _URL_UNRESERVED_CHARS + _URL_GEN_DELIMS + _URL_SUB_DELIMS
URL_CHAR_REGEX: Final = f"^[{URL_CHAR_REGEX_CHARS}]+$"

# A Watofolder has a foldername when storing it on disk, with only some valid
# chars. In the UI nearly everything is allowed. So these Regex(es) are only
# for the names on disk
WATO_FOLDER_PATH_NAME_CHARS: Final = r"-\w"
WATO_FOLDER_PATH_NAME_REGEX: Final = f"^[{WATO_FOLDER_PATH_NAME_CHARS}]*\\Z"

GROUP_NAME_PATTERN: Final = r"^(?!\.\.$|\.$)[-a-zA-Z0-9_\.]*\Z"


def regex(pattern: str, flags: int = 0) -> re.Pattern[str]:
    """Compile regex or look it up in already compiled regexes.
    (compiling is a CPU consuming process. We cache compiled regexes)."""
    with contextlib.suppress(KeyError):
        return g_compiled_regexes[(pattern, flags)]
    try:
        reg = re.compile(pattern, flags=flags)
    except Exception as e:
        raise MKGeneralException(_("Invalid regular expression '%s': %s") % (pattern, e))

    g_compiled_regexes[(pattern, flags)] = reg
    return reg


def is_regex(pattern: str) -> bool:
    """Checks if a string contains characters that make it necessary
    to use regular expression logic to handle it correctly"""
    return any(c in ".?*+^$|[](){}\\" for c in pattern)


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
    return re.sub(r"\\(.)", r"\1", pattern)
