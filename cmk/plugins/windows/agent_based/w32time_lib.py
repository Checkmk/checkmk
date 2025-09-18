#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Helper functions for parsing the output of `w32tm /query ...`
"""

import itertools
import re


def parse_int(value: str) -> int:
    value = value.replace("s", "")
    return int(value)


def parse_float(value: str) -> float:
    value = value.replace("s", "")
    return float(value)


def parse_hex(value: str) -> int:
    value = value.replace("s", "")
    return int(value, 16)


def before_parens(value: str) -> str:
    return "".join(itertools.takewhile(lambda c: c != "(", value)).strip()


def in_parens(value: str) -> str:
    matches = re.search(r"\(([^)]*)\)", value)
    return matches.group(1) if matches else ""
