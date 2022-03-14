#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union

from .agent_based_api.v1 import check_levels, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.wlc_clients import ClientsPerInterface, ClientsTotal, VsResult, WlcClientsSection


def discover_wlc_clients(
    section: Union[WlcClientsSection[ClientsTotal], WlcClientsSection[ClientsPerInterface]],
) -> DiscoveryResult:
    if not section.clients_per_ssid:
        return
    yield Service(item="Summary")
    for ssid_name in section.clients_per_ssid.keys():
        yield Service(item=ssid_name)


def check_wlc_clients(
    item: str,
    params: VsResult,
    section: Union[WlcClientsSection[ClientsTotal], WlcClientsSection[ClientsPerInterface]],
) -> CheckResult:
    description = ""
    if item == "Summary":
        total_number_of_clients = section.total_clients
    else:
        clients_ssid = section.clients_per_ssid[item]
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

    yield from check_levels(
        total_number_of_clients,
        levels_upper=params.get("levels"),
        levels_lower=params.get("levels_lower"),
        metric_name="connections",
        label="Connections",
        render_func=lambda value: str(int(value)),
    )
    if description:
        yield Result(state=State.OK, summary=description)


register.check_plugin(
    name="wlc_clients",
    service_name="Clients %s",
    discovery_function=discover_wlc_clients,
    check_default_parameters={},
    check_ruleset_name="wlc_clients",
    check_function=check_wlc_clients,
)
