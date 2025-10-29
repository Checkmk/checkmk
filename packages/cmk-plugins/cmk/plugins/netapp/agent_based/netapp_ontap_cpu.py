#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.netapp import models

Section = Mapping[str, models.NodeModel]


def parse_netapp_ontap_cpu(string_table: StringTable) -> Section:
    return {
        node_obj.name: node_obj
        for node in string_table
        for node_obj in [models.NodeModel.model_validate_json(node[0])]
    }


agent_section_netapp_ontap_cpu = AgentSection(
    name="netapp_ontap_node",
    parse_function=parse_netapp_ontap_cpu,
)


def inventory_netapp_ontap_cpu(section: Section) -> DiscoveryResult:
    yield from (Service(item=item_name) for item_name in section)


def check_netapp_ontap_cpu_utilization(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    yield from check_cpu_util(
        util=data.processor_utilization,
        params=params,
        value_store=get_value_store(),
        this_time=data.processor_utilization_timestamp.timestamp(),
    )

    if data.cpu_count is not None:
        yield Result(state=State.OK, summary=f"Number of CPUs: {data.cpu_count} CPUs")


check_plugin_netapp_ontap_cpu = CheckPlugin(
    name="netapp_ontap_cpu",
    service_name="CPU utilization Node %s",
    discovery_function=inventory_netapp_ontap_cpu,
    sections=["netapp_ontap_node"],
    check_function=check_netapp_ontap_cpu_utilization,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)


def discovery_netapp_ontap_nvram_bat(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_netapp_ontap_nvram_bat(item: str, section: Section) -> CheckResult:
    state_map = {
        "battery_ok": State.OK,
        "battery_partially_discharged": State.OK,
        "battery_fully_discharged ": State.CRIT,
        "battery_not_present": State.CRIT,
        "battery_near_end_of_life": State.WARN,
        "battery_at_end_of_life": State.CRIT,
        "battery_unknown": State.UNKNOWN,
        "battery_over_charged": State.WARN,
        "battery_fully_charged": State.OK,
    }

    if (data := section.get(item)) is None:
        return

    yield Result(
        state=state_map.get(data.battery_state, State.UNKNOWN),
        summary=f"Status: {data.battery_state.replace('_', ' ').title()}",
    )


check_plugin_netapp_ontap_nvram_bat = CheckPlugin(
    name="netapp_ontap_cpu_nvram_bat",
    service_name="NVRAM Battery %s",
    sections=["netapp_ontap_node"],
    discovery_function=discovery_netapp_ontap_nvram_bat,
    check_function=check_netapp_ontap_nvram_bat,
)
