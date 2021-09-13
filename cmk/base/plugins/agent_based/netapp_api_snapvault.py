#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_api_vf_snapvault:sep(9)>>>
# snapvault /vol/ipb_datap/   status idle state snapvaulted   lag-time 53812  source-system 172.31.12.15
# snapvault /vol/ipb_datas/   status idle state snapvaulted   lag-time 53812  source-system 172.31.12.15
# snapvault /vol/ipb_user/    status idle state snapvaulted   lag-time 97007  source-system 172.31.12.15
# snapvault /vol/ipb_vol0/    status idle state snapvaulted   lag-time 97011  source-system 172.31.12.15

# Netapp clustermode:
# <<<netapp_api_snapvault:sep(9)>>>
# snapvault my_snap	state snapmirrored	source-system c1	destination-location d3:my_snap	policy ABCDefault	lag-time 91486	destination-system a2-b0-02	status idle
# snapvault my_snap	state snapmirrored	source-system i1	destination-location d1:my_snap	policy Default	lag-time 82486	destination-system a2-b0-02	status idle
# snapvault my_snap	state snapmirrored	source-system t1	destination-location d2:my_snap	policy Default	lag-time 73487	destination-system a2-b0-02	status idle

from typing import Any, Dict, Iterable, Mapping, OrderedDict, Tuple

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.netapp_api import SectionSingleInstance


def _cleanse_item_name(name: str) -> str:
    return name.replace("$", "_")


def parse_netapp_api_snapvault(string_table: StringTable) -> SectionSingleInstance:
    section = {}
    for line in string_table:
        parsed_line = dict(tuple(i.split(" ", 1)) for i in line)  # type: ignore
        # Whether the item will be named after the snapvault or destination-location
        # values depends on the user's configuration (discovery parameters). For simplicity,
        # the same line is referenced to both in the parsed dictionary, so that the items
        # can easily be retrieved using the .get method, without needing to worry
        # about what the discovery parameters are.
        section[_cleanse_item_name(parsed_line["snapvault"])] = parsed_line
        if "destination-location" in parsed_line:
            # 7mode netapp data comes without destination-location. We currently do not have
            # a test case for this.
            section[_cleanse_item_name(parsed_line["destination-location"])] = parsed_line
    return section


register.agent_section(
    name="netapp_api_snapvault",
    parse_function=parse_netapp_api_snapvault,
)


def _prefilter_items(
    parsed: SectionSingleInstance,
    exclude_vserver: bool,
) -> Iterable[Tuple[str, Dict[str, str]]]:
    if exclude_vserver:
        return [i for i in parsed.items() if ":" not in i[0]]
    return [i for i in parsed.items() if ":" in i[0] or "destination-location" not in i[1]]


def discover_netapp_api_snapvault(
    params: Mapping[str, Any],
    section: SectionSingleInstance,
) -> DiscoveryResult:
    for snapvault, values in _prefilter_items(section, params["exclude_destination_vserver"]):
        if "lag-time" in values:
            yield Service(item=snapvault)


def check_netapp_api_snapvault(
    item: str,
    params: Mapping[str, Any],
    section: SectionSingleInstance,
) -> CheckResult:
    snapvault = section.get(item)
    if not snapvault:
        return

    for key in ["source-system", "destination-system", "policy", "status", "state"]:
        if key in snapvault:
            yield Result(state=State.OK, summary="%s: %s" % (key.title(), snapvault[key]))

    if "lag-time" not in snapvault:
        return

    lag_time = int(snapvault["lag-time"])

    policy_lag_time = OrderedDict(params.get("policy_lag_time", []))
    levels = policy_lag_time.get(snapvault.get("policy"))

    if not levels:
        levels = params.get("lag_time", (None, None))

    yield from check_levels(
        value=lag_time,
        levels_upper=levels,
        render_func=render.timespan,
        label="Lag time",
    )


register.check_plugin(
    name="netapp_api_snapvault",
    sections=["netapp_api_snapvault"],
    service_name="Snapvault %s",
    discovery_function=discover_netapp_api_snapvault,
    discovery_ruleset_name="discovery_snapvault",
    discovery_default_parameters={"exclude_destination_vserver": False},
    check_function=check_netapp_api_snapvault,
    check_ruleset_name="snapvault",
    check_default_parameters={},
)
