#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from .agent_based_api.v1 import register, type_defs


def parse_systemtime(string_table: type_defs.StringTable) -> Dict[str, float]:
    """
    >>> parse_systemtime([['12345']])
    {'foreign_systemtime': 12345.0}
    >>> parse_systemtime([['12345.2', '567.3']])
    {'foreign_systemtime': 12345.2, 'our_systemtime': 567.3}
    >>> parse_systemtime([[]])
    {}
    """
    return {
        key: float(value)
        for key, value in zip(["foreign_systemtime", "our_systemtime"], string_table[0])
    }


register.agent_section(
    name="systemtime",
    parse_function=parse_systemtime,
)
