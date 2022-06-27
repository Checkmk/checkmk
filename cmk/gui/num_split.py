#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from typing import List, Optional, Tuple, Union

from cmk.gui.hooks import request_memoize


@request_memoize(maxsize=100000)
def num_split(s: str) -> Tuple[Union[int, str], ...]:
    """Splits a word into sequences of numbers and non-numbers.

    Creates a tuple from these where the number are converted into int datatype.
    That way a naturual sort can be implemented.
    """
    parts: List[Union[int, str]] = []
    for part in re.split(r"(\d+)", s):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)

    return tuple(parts)


@request_memoize(maxsize=100000)
def cmp_num_split(a: str, b: str) -> int:
    """Compare two strings, separate numbers and non-numbers from before."""
    return (num_split(a) > num_split(b)) - (num_split(a) < num_split(b))


def key_num_split(a: str) -> Tuple[Union[int, str], ...]:
    """Return a key from a string, separate numbers and non-numbers from before."""
    return num_split(a)


def cmp_version(a: Optional[str], b: Optional[str]) -> int:
    """Compare two version numbers with each other
    Allow numeric version numbers, but also characters.
    """
    if a is None or b is None:
        if a is None:
            a = ""
        if b is None:
            b = ""
        return (a > b) - (a < b)
    aa = list(map(num_split, a.split(".")))
    bb = list(map(num_split, b.split(".")))
    return (aa > bb) - (aa < bb)
