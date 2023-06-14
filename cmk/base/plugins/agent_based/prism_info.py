#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from collections.abc import Mapping
from typing import Any

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import load_json

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_info(string_table: StringTable) -> Section:
    return load_json(string_table)


register.agent_section(
    name="prism_info",
    parse_function=parse_prism_info,
)


def discovery_prism_info(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_info(section: Section) -> CheckResult:
    if section:
        summary = (
            f"Name: {section.get('name')}, "
            f"Version: {section.get('version')}, "
            f"Nodes: {section.get('num_nodes')}"
        )

        yield Result(
            state=State.OK,
            summary=summary,
        )


register.check_plugin(
    name="prism_info",
    service_name="NTNX Cluster",
    sections=["prism_info"],
    discovery_function=discovery_prism_info,
    check_function=check_prism_info,
)
