#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Dict, List

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

OID_SysDesc = ".1.3.6.1.2.1.1.1.0"
OID_SysObjectID = ".1.3.6.1.2.1.1.2.0"


class DeviceStatus(Enum):
    ACTIVE = 1
    DEACTIVE = 2
    NOT_INSTALLED = 3
    UNSUPPORTED = 4


Section = Dict[str, int]


def parse_hp_hh3c_device(string_table: List[StringTable]) -> Section:
    return {s[0]: int(s[1]) for s in string_table[0]}


def discover_hp_hh3c_device(section: Section) -> DiscoveryResult:
    for num, status in section.items():
        if status not in (DeviceStatus.UNSUPPORTED.value, DeviceStatus.NOT_INSTALLED.value):
            yield Service(item=num)


def check_hp_hh3c_device(item: str, section: Section) -> CheckResult:
    status = section.get(item)
    if status is None:
        return

    if status == DeviceStatus.DEACTIVE.value:
        yield Result(state=State.CRIT, summary="Status: deactive")
    else:
        yield Result(state=State.OK, summary="Status: active")
