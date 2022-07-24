#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
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


def discovery_netapp_api_psu(
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
) -> DiscoveryResult:
    if not netapp_api.discover_single_items(params):
        return
    yield from (Service(item=key) for key in section)


def check_netapp_api_psu(
    item: str,
    section: netapp_api.SectionSingleInstance,
) -> CheckResult:
    if not (psu := section.get(item)):
        return

    if psu.get("power-supply-is-error") == "true":
        yield Result(
            state=State.CRIT, summary="Error in PSU %s" % psu["power-supply-element-number"]
        )
    else:
        yield Result(state=State.OK, summary="Operational state OK")


register.check_plugin(
    name="netapp_api_psu",
    service_name="Power Supply Shelf %s",
    discovery_function=discovery_netapp_api_psu,
    discovery_ruleset_name="discovery_netapp_api_psu_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_api_psu,
)


def discovery_netapp_api_psu_summary(
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
) -> DiscoveryResult:
    if not section or netapp_api.discover_single_items(params):
        return
    yield Service(item="Summary")


def _get_failed_power_supply_elements(psus: Mapping[str, netapp_api.Instance]) -> Sequence[str]:
    return [key for key, value in psus.items() if value.get("power-supply-is-error") == "true"]


def check_netapp_api_psu_summary(
    item: str,
    section: netapp_api.SectionSingleInstance,
):
    yield Result(state=State.OK, summary=f"{len(section)} power supply units in total")

    erred_psus = _get_failed_power_supply_elements(section)
    if erred_psus:
        erred_psus_names = ", ".join(erred_psus)
        count = len(erred_psus)
        yield Result(
            state=State.CRIT,
            summary="%d power supply unit%s in error state (%s)"
            % (
                count,
                "" if count == 1 else "s",
                erred_psus_names,
            ),
        )


register.check_plugin(
    name="netapp_api_psu_summary",
    service_name="Power Supply Shelf %s",
    sections=["netapp_api_psu"],
    discovery_function=discovery_netapp_api_psu_summary,
    discovery_ruleset_name="discovery_netapp_api_psu_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_api_psu_summary,
)
