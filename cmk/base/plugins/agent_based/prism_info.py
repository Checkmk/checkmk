#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from typing import Any, Dict

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[Any, Any]


def parse_prism_info(string_table: StringTable) -> Section:
    import ast

    data = ast.literal_eval(string_table[0][0])
    return data


register.agent_section(
    name="prism_info",
    parse_function=parse_prism_info,
)


def discovery_prism_info(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_info(section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary="Name: %s, Version: %s" % (section.get("name"), section.get("version")),
    )


register.check_plugin(
    name="prism_info",
    service_name="NTNX Cluster",
    sections=["prism_info"],
    discovery_function=discovery_prism_info,
    check_function=check_prism_info,
)
