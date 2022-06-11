#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, TypedDict

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


class Section(TypedDict, total=False):
    system_config: Mapping[str, str]
    update_required: bool
    cpu: Mapping[str, float]
    util: Mapping[str, tuple[float, str]]


def parse_lparstat_aix(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    if len(string_table) < 4:
        return {"update_required": True}

    # get system config:
    kv_pairs = (word for word in string_table[0] if "=" in word)
    system_config = dict(kv.split("=", 1) for kv in kv_pairs)
    # from ibm.com: 'If there are two SMT threads, the row is displayed as "on."'
    if system_config.get("smt", "").lower() == "on":
        system_config["smt"] = "2"

    cpu = {}
    util = {}
    for index, key in enumerate(string_table[1]):
        name = key.lstrip("%")
        uom = "%" if "%" in key else ""
        try:
            value = float(string_table[3][index])
        except (IndexError, ValueError):
            continue

        if name in ("user", "sys", "idle", "wait"):
            cpu[name] = value
        else:
            util[name] = (value, uom)

    return {
        "system_config": system_config,
        "util": util,
        "cpu": cpu,
    }


register.agent_section(
    name="lparstat_aix",
    parse_function=parse_lparstat_aix,
)
