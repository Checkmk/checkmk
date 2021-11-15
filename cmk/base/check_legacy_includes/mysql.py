#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import functools
from typing import Any, Callable, Dict, Mapping, MutableSequence, Sequence


def mysql_parse_per_item(
    parse_function: Callable[[Sequence[Sequence[str]]], Any]
) -> Callable[[Sequence[Sequence[str]]], Mapping[str, Any]]:
    @functools.wraps(parse_function)
    def wrapped_parse_function(info: Sequence[Sequence[str]]) -> Mapping[str, Any]:
        item = "mysql"
        grouped: Dict[str, MutableSequence[Sequence[str]]] = {}
        for line in info:
            if line[0].startswith("[["):
                item = " ".join(line).strip("[ ]") or item
                continue
            grouped.setdefault(item, []).append(line)
        return {k: parse_function(grouped[k]) for k in grouped}

    return wrapped_parse_function
