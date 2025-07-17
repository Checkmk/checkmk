#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re


def format_php(data: object, lvl: int = 1) -> str:
    """Format a Python object as PHP code."""
    s = ""
    if isinstance(data, list | tuple):
        s += "array(\n"
        for item in data:
            s += "    " * lvl + format_php(item, lvl + 1) + ",\n"
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, dict):
        s += "array(\n"
        for key, val in data.items():
            s += "    " * lvl + format_php(key, lvl + 1) + " => " + format_php(val, lvl + 1) + ",\n"
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, str):
        s += "'%s'" % re.sub(r"('|\\)", r"\\\1", data)
    elif isinstance(data, bool):
        s += "true" if data else "false"
    elif isinstance(data, int | float):
        s += str(data)
    elif data is None:
        s += "null"
    else:
        s += format_php(str(data))
    return s
