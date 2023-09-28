#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import netapp_api

# <<<netapp_api_psu:sep(9)>>>
# power-supply-list 20    is-auto-power-reset-enabled false   power-supply-part-no 114-00065+A2 ...
# power-supply-list 20    is-auto-power-reset-enabled false   power-supply-part-no 114-00065+A2 ...


def _format_item(name: str, _instance: netapp_api.Instance) -> str:
    return name.replace(".", "/")


def parse_netapp_api_psu(string_table: StringTable) -> netapp_api.SectionSingleInstance:
    return {
        name: psu
        for name, psu in netapp_api.parse_netapp_api_single_instance(
            string_table,
            custom_keys=["power-supply-list", "power-supply-element-number"],
            item_func=_format_item,
        ).items()
        if psu.get("power-supply-is-not-installed") != "true"
    }


register.agent_section(
    name="netapp_api_psu",
    parse_function=parse_netapp_api_psu,
)


register.check_plugin(
    name="netapp_api_psu",
    service_name="Power Supply Shelf %s",
    discovery_function=netapp_api.discover_single,
    discovery_ruleset_name="discovery_netapp_api_psu_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=netapp_api.get_single_check("power supply unit"),
)


register.check_plugin(
    name="netapp_api_psu_summary",
    service_name="Power Supply Shelf %s",
    sections=["netapp_api_psu"],
    discovery_function=netapp_api.discover_summary,
    discovery_ruleset_name="discovery_netapp_api_psu_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=netapp_api.get_summary_check("power supply unit"),
)
