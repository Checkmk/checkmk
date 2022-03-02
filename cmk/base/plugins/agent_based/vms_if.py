#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, type_defs
from .utils import interfaces


def wrap_negative(str_value: str) -> float:
    # Due to signed 32-bit arithmetics we sometimes get negative values. Those must be converted to
    # positive ones.
    c = interfaces.saveint(str_value)
    return c + 2**32 if c < 0 else c


_VMS_IF_COUNTERS_ORDER = [
    "in_octets",
    "in_ucast",
    "in_mcast",
    "in_bcast",
    "in_discards",
    "in_errors",
    "out_octets",
    "out_ucast",
    "out_mcast",
    "out_bcast",
    "out_discards",
    "out_errors",
]


def parse_vms_if(string_table: type_defs.StringTable) -> interfaces.Section:
    return [
        interfaces.Interface(
            index=str(idx + 1),
            descr=line[0],
            alias=line[0],
            type="6",  # Ethernet
            speed=1000000000,
            oper_status="1",
            **{  # type: ignore[arg-type]
                counter: wrap_negative(str_val)
                for counter, str_val in zip(_VMS_IF_COUNTERS_ORDER, line[1:])
            },
        )
        for idx, line in enumerate(string_table)
    ]


register.agent_section(
    name="vms_if",
    parse_function=parse_vms_if,
    parsed_section_name="interfaces",
)
