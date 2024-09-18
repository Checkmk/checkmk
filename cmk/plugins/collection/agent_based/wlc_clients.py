#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.lib.wlc_clients import (
    ClientsPerInterface,
    ClientsTotal,
    VsResult,
    WlcClientsSection,
)


def discover_wlc_clients(
    section: WlcClientsSection[ClientsTotal] | WlcClientsSection[ClientsPerInterface],
) -> DiscoveryResult:
    if not section.clients_per_ssid:
        return
    yield Service(item="Summary")
    for ssid_name in section.clients_per_ssid.keys():
        yield Service(item=ssid_name)


def check_wlc_clients(
    item: str,
    params: VsResult,
    section: WlcClientsSection[ClientsTotal] | WlcClientsSection[ClientsPerInterface],
) -> CheckResult:
    description = ""
    if item == "Summary":
        total_number_of_clients = section.total_clients
    else:
        if (clients_ssid := section.clients_per_ssid.get(item)) is None:
            return
        if isinstance(clients_ssid, ClientsTotal):
            total_number_of_clients = clients_ssid.total
        else:
            total_number_of_clients = sum(clients_ssid.per_interface.values())
            description = "({})".format(
                ", ".join(  #
                    f"{interface}: {number_of_clients}"  #
                    for interface, number_of_clients in clients_ssid.per_interface.items()  #
                )
            )

    yield from check_levels_v1(
        total_number_of_clients,
        levels_upper=params.get("levels"),
        levels_lower=params.get("levels_lower"),
        metric_name="connections",
        label="Connections",
        render_func=lambda value: str(int(value)),
    )
    if description:
        yield Result(state=State.OK, summary=description)


check_plugin_wlc_clients = CheckPlugin(
    name="wlc_clients",
    service_name="Clients %s",
    discovery_function=discover_wlc_clients,
    check_default_parameters={},
    check_ruleset_name="wlc_clients",
    check_function=check_wlc_clients,
)
