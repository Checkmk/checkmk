#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.netapp import models

Section = Sequence[models.AgentInfoModel]


def parse_netapp_ontap_agent_info(string_table: StringTable) -> Section:
    return [models.AgentInfoModel.model_validate_json(line[0]) for line in string_table]


def discover_netapp_ontap_agent_info(section: Section) -> DiscoveryResult:
    yield Service()


def check_netapp_ontap_agent_info(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No errors")
        return

    for info in section:
        yield Result(
            state=State.WARN if info.is_error else State.OK,
            summary=f"{info.section}: {info.info}",
        )


agent_section_netapp_ontap_agent_info = AgentSection(
    name="netapp_ontap_agent_info",
    parse_function=parse_netapp_ontap_agent_info,
)

check_plugin_netapp_ontap_agent_info = CheckPlugin(
    name="netapp_ontap_agent_info",
    service_name="NetApp ONTAP Agent info",
    discovery_function=discover_netapp_ontap_agent_info,
    check_function=check_netapp_ontap_agent_info,
)
