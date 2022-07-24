#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
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


def discovery_netapp_api_fan(
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
) -> DiscoveryResult:
    if not netapp_api.discover_single_items(params):
        return
    yield from (Service(item=item) for item in section)


def check_netapp_api_fan(
    item: str,
    section: netapp_api.SectionSingleInstance,
) -> CheckResult:
    if not (fan := section.get(item)):
        return

    if fan["cooling-element-is-error"] == "true":
        yield Result(state=State.CRIT, summary="Error in Fan %s" % fan["cooling-element-number"])
    else:
        yield Result(state=State.OK, summary="Operational state OK")


register.check_plugin(
    name="netapp_api_fan",
    service_name="Fan Shelf %s",
    discovery_function=discovery_netapp_api_fan,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_api_fan,
)


def discovery_netapp_api_fan_summary(
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
) -> DiscoveryResult:
    if not section or netapp_api.discover_single_items(params):
        return
    yield Service(item="Summary")


def _get_failed_cooling_elements(fans: Mapping[str, netapp_api.Instance]) -> Sequence[str]:
    erred_fans = []
    for key, value in fans.items():
        if value["cooling-element-is-error"] == "true":
            erred_fans.append(key)
    return erred_fans


def check_netapp_api_fan_summary(
    item: str,
    section: netapp_api.SectionSingleInstance,
) -> CheckResult:
    yield Result(state=State.OK, summary=f"{len(section)} fans in total")

    erred_fans = _get_failed_cooling_elements(section)
    if erred_fans:
        erred_fans_names = ", ".join(erred_fans)
        count = len(erred_fans)
        yield Result(
            state=State.CRIT,
            summary="%d fan%s in error state (%s)"
            % (
                count,
                "" if count == 1 else "s",
                erred_fans_names,
            ),
        )


register.check_plugin(
    name="netapp_api_fan_summary",
    service_name="Fan Shelf %s",
    sections=["netapp_api_fan"],
    discovery_function=discovery_netapp_api_fan_summary,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_api_fan_summary,
)
