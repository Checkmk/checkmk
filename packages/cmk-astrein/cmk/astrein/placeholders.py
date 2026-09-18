#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Detection of printf-style positional placeholders.

Shared by the logging and localization checkers, both of which forbid positional
``%s``/``%d`` in favour of named ``%(name)s`` placeholders.
"""

import re

#: A single printf-style conversion specifier, per the Python spec:
#: https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
#: The mapping key is captured to tell ``%(name)s`` from ``%s``.
PRINTF_SPEC = re.compile(
    r"%"
    r"(?:\((?P<key>[^)]*)\))?"  # optional mapping key
    r"[#0\- +]*"  # conversion flags
    r"(?:\*|\d+)?"  # minimum field width
    r"(?:\.(?:\*|\d+))?"  # precision
    r"[hlL]?"  # length modifier (accepted but ignored by Python)
    r"(?P<type>[diouxXeEfFgGcrsa%])"  # conversion type
)


def has_positional_placeholder(format_string: str) -> bool:
    """Return True if ``format_string`` has a positional ``%s`` rather than ``%(name)s``.

    The literal ``%%`` is ignored.
    """
    return any(
        match.group("type") != "%" and match.group("key") is None
        for match in PRINTF_SPEC.finditer(format_string)
    )
