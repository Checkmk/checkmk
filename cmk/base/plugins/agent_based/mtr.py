#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Sequence

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


class Hop(NamedTuple):
    name: str
    pl: float
    response_time: float
    rta: float
    rtmin: float
    rtmax: float
    rtstddev: float


Section = Mapping[str, Sequence[Hop]]


def parse_mtr(string_table: StringTable) -> Section:
    return {
        hostname: [
            Hop(
                name=rest[0 + 8 * hopnum],
                pl=float(rest[1 + 8 * hopnum].replace("%", "").rstrip()),
                response_time=float(rest[3 + 8 * hopnum]) / 1000,
                rta=float(rest[4 + 8 * hopnum]) / 1000,
                rtmin=float(rest[5 + 8 * hopnum]) / 1000,
                rtmax=float(rest[6 + 8 * hopnum]) / 1000,
                rtstddev=float(rest[7 + 8 * hopnum]) / 1000,
            ) for hopnum in range(hopcount)
        ] for line in string_table
        for hostname, hopcount, rest in [(line[0], int(float(line[2])), line[3:])]
        if line and not line[0].startswith("**ERROR**")
    }


register.agent_section(
    name="mtr",
    parse_function=parse_mtr,
)
