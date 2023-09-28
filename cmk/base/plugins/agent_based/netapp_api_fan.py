#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import netapp_api

# <<<netapp_api_fan:sep(9)>>>
# cooling-element-list 20 cooling-element-number 1    rpm 3000    cooling-element-is-error false
# cooling-element-list 20 cooling-element-number 2    rpm 3000    cooling-element-is-error false
# cooling-element-list 20 cooling-element-number 3    rpm 3000    cooling-element-is-error false


def _format_item(name: str, _instance: netapp_api.Instance) -> str:
    return name.replace(".", "/")


def parse_netapp_api_fan(string_table: StringTable) -> netapp_api.SectionSingleInstance:
    return {
        name: fan
        for name, fan in netapp_api.parse_netapp_api_single_instance(
            string_table,
            custom_keys=["cooling-element-list", "cooling-element-number"],
            item_func=_format_item,
        ).items()
        if fan.get("cooling-element-is-not-installed") != "true"
    }


register.agent_section(
    name="netapp_api_fan",
    parse_function=parse_netapp_api_fan,
)


register.check_plugin(
    name="netapp_api_fan",
    service_name="Fan Shelf %s",
    discovery_function=netapp_api.discover_single,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=netapp_api.get_single_check("fan"),
)


register.check_plugin(
    name="netapp_api_fan_summary",
    service_name="Fan Shelf %s",
    sections=["netapp_api_fan"],
    discovery_function=netapp_api.discover_summary,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=netapp_api.get_summary_check("fan"),
)
