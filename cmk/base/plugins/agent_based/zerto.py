#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Optional

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass
class Section:
    has_errors: bool
    error_details: Optional[str] = None


def parse(string_table: StringTable) -> Section:
    for line in string_table:
        if "Error" in line[0]:
            return Section(True, error_details=" ".join(line[0].split(":")[1:]).strip())

    return Section(False)


register.agent_section(name="zerto_agent", parse_function=parse)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(section: Section) -> CheckResult:
    if section.has_errors:
        yield Result(
            state=State.CRIT,
            summary="Error starting agent",
            details=section.error_details,
        )
    else:
        yield Result(state=State.OK, summary="Agent started without problem")


register.check_plugin(
    name="zerto_agent",
    service_name="Zerto Agent Status",
    discovery_function=discovery,
    check_function=check,
)
