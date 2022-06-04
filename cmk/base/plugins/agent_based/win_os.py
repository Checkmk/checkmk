#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from dataclasses import asdict, dataclass
from typing import Literal

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


@dataclass
class Section:
    name: str
    kernel_version: str
    arch: Literal["x86_64", "i386"]
    service_pack: str
    install_date: int


def parse_win_os(string_table: StringTable) -> Section:
    (
        (_cryptic_name, name, kernel_version, arch, service_pack_maj, service_pack_min, date_str),
    ) = string_table

    if "+" in date_str:
        (datestr, tz), sign = date_str.split("+", 1), 1
    elif "-" in date_str:
        (datestr, tz), sign = date_str.split("-"), -1
    else:
        datestr, tz, sign = date_str, "0", 1
    offset = sign * int(tz) * 60

    return Section(
        name=name,
        kernel_version=kernel_version,
        arch="x86_64" if arch.lower() == "64-bit" else "i386",
        service_pack=f"{service_pack_maj}.{service_pack_min}",
        install_date=int(time.mktime(time.strptime(datestr, "%Y%m%d%H%M%S.%f"))) - offset,
    )


register.agent_section(
    name="win_os",
    parse_function=parse_win_os,
)


def inventory_win_os(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "type": "Windows",
            "vendor": "Microsoft",
            **asdict(section),
        },
    )


register.inventory_plugin(
    name="win_os",
    inventory_function=inventory_win_os,
)
