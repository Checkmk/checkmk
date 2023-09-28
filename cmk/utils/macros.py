#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

MacroMapping = MutableMapping[str, str]


def replace_macros_in_str(string: str, macro_mapping: MacroMapping) -> str:
    """
    >>> replace_macros_in_str("abc $MACRO$ 123", {"$MACRO$": "replacement", })
    'abc replacement 123'
    >>> replace_macros_in_str("abc $MACRO$ 123", {"$MACRO2$": "replacement2"})
    'abc $MACRO$ 123'
    """
    for macro, replacement in macro_mapping.items():
        string = string.replace(macro, replacement)
    return string
