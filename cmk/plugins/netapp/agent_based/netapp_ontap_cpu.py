#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State
from cmk.agent_based.v2.type_defs import CheckResult, DiscoveryResult, StringTable
from cmk.plugins.netapp import models

Section = Mapping[str, models.NodeModel]

# <<<netapp_ontap_node:sep(0)>>>
# {
#     "controller": {"cpu": {"count": 36, "processor": "Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz"}},
#     "model": "AFF-A700",
#     "name": "mcc_darz_a-02",
#     "nvram": {"battery_state": "battery_ok"},
#     "serial_number": "211709000156",
#     "system_id": "0537063878",
#     "uuid": "1e13de87-bda2-11ed-b8bd-00a098c50e5b",
#     "version": {
#         "full": "NetApp Release 9.12.1P6: Fri Aug 04 00:26:53 UTC 2023",
#         "generation": 9,
#         "major": 12,
#         "minor": 1,
#     },
# }
# {
#     "controller": {"cpu": {"count": 36, "processor": "Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz"}},
#     "model": "AFF-A700",
#     "name": "mcc_darz_a-01",
#     "nvram": {"battery_state": "battery_ok"},
#     "serial_number": "211709000155",
#     "system_id": "0537063936",
#     "uuid": "8f2677e2-bda7-11ed-88df-00a098c54c0b",
#     "version": {
#         "full": "NetApp Release 9.12.1P6: Fri Aug 04 00:26:53 UTC 2023",
#         "generation": 9,
#         "major": 12,
#         "minor": 1,
#     },
# }


def parse_netapp_ontap_cpu(string_table: StringTable) -> Section:
    return {
        node_obj.name: node_obj
        for node in string_table
        if (node_obj := models.NodeModel.model_validate_json(node[0]))
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

    if data.cpu_count is not None:
        yield Result(state=State.OK, summary=f"Total CPU: {data.cpu_count} CPUs")
    else:
        yield Result(state=State.UNKNOWN, summary="No available CPU data")


check_plugin_netapp_ontap_cpu = CheckPlugin(
    name="netapp_ontap_cpu",
    service_name="CPU Node %s",
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
