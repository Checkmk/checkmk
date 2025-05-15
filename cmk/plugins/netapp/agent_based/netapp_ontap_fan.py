#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, CheckPlugin, CheckResult, StringTable
from cmk.plugins.netapp import models
from cmk.plugins.netapp.agent_based import lib as netapp_api

Section = Mapping[str, models.ShelfFanModel]

# <<<netapp_ontap_fan:sep(0)>>>
# {
#     "fans": [
#         {"id": 1, "rpm": 3030, "state": "ok"},
#         {"id": 2, "rpm": 2970, "state": "ok"},
#         {"id": 3, "rpm": 3030, "state": "ok"},
#         {"id": 4, "rpm": 3000, "state": "ok"},
#     ],
#     "id": "10",
# }
# {
#     "fans": [
#         {"id": 1, "rpm": 2970, "state": "ok"},
#         {"id": 2, "rpm": 3030, "state": "ok"},
#         {"id": 3, "rpm": 3000, "state": "ok"},
#         {"id": 4, "rpm": 3060, "state": "ok"},
#     ],
#     "id": "20",
# }


def _get_section_single_instance(section: Section) -> netapp_api.SectionSingleInstance:
    # see netapp_api._DEV_KEYS["fan"]
    error_key, number_key = netapp_api.DEV_KEYS["fan"]

    return {
        key: {error_key: str(val.state == "error").lower(), number_key: key}
        for key, val in section.items()
    }


def parse_netapp_ontap_fan(string_table: StringTable) -> Section:
    return {
        fan.item_name(): fan
        for line in string_table
        if (fan := models.ShelfFanModel.model_validate_json(line[0])) is not None
        and fan.consider_installed()
    }


agent_section_netapp_ontap_fan = AgentSection(
    name="netapp_ontap_fan",
    parse_function=parse_netapp_ontap_fan,
)


def check_netapp_ontap_fan(item: str, section: Section) -> CheckResult:
    yield from netapp_api.get_single_check("fan")(item, _get_section_single_instance(section))


check_plugin_netapp_ontap_fan = CheckPlugin(
    name="netapp_ontap_fan",
    service_name="Fan Shelf %s",
    sections=["netapp_ontap_fan"],
    discovery_function=netapp_api.discover_single,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_ontap_fan,
)


def check_netapp_ontap_fan_summary(
    item: str,
    section: Section,
) -> CheckResult:
    yield from netapp_api.get_summary_check("fan")(item, _get_section_single_instance(section))


check_plugin_netapp_ontap_fan_summary = CheckPlugin(
    name="netapp_ontap_fan_summary",
    service_name="Fan Shelf %s",
    sections=["netapp_ontap_fan"],
    discovery_function=netapp_api.discover_summary,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_ontap_fan_summary,
)
