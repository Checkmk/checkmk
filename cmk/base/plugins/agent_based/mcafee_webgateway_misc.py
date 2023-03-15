#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils import mcafee_gateway


@dataclasses.dataclass
class Section:
    client_count: typing.Optional[int]
    socket_count: typing.Optional[int]


class Params(typing.TypedDict, total=True):
    clients: typing.NotRequired[typing.Tuple[int, int]]
    network_sockets: typing.NotRequired[typing.Tuple[int, int]]


def parse_mcafee_webgateway_misc(
    string_table: v1.type_defs.StringTable,
) -> typing.Optional[Section]:
    if not string_table:
        return None
    # -- Miscellaneous (these counter are NO lifetime counter; they show the actual number)
    # .1.3.6.1.4.1.1230.2.7.2.5.2.0 16 --> MCAFEE-MWG-MIB::stClientCount.0
    # .1.3.6.1.4.1.1230.2.7.2.5.3.0 35 --> MCAFEE-MWG-MIB::stConnectedSockets.0
    clients_str, sockets_str = string_table[0]
    return Section(
        client_count=int(clients_str) if clients_str.isdigit() else None,
        socket_count=int(sockets_str) if sockets_str.isdigit() else None,
    )


v1.register.snmp_section(
    name="mcafee_webgateway_misc",
    parse_function=parse_mcafee_webgateway_misc,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.5",
        oids=[
            "2",  # MCAFEE-MWG-MIB::stClientCount
            "3",  # MCAFEE-MWG-MIB::stConnectedSockets
        ],
    ),
    detect=mcafee_gateway.DETECT_WEB_GATEWAY,
)


def discovery_mcafee_webgateway_misc(section: Section) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def check_mcafee_webgateway_misc(params: Params, section: Section) -> v1.type_defs.CheckResult:
    if section.client_count is not None:
        yield from v1.check_levels(
            section.client_count,
            levels_upper=params.get("clients"),
            metric_name="connections",
            label="Clients",
            render_func=str,
        )
    if section.socket_count is not None:
        yield from v1.check_levels(
            section.socket_count,
            levels_upper=params.get("network_sockets"),
            metric_name="open_network_sockets",
            label="Open network sockets",
            render_func=str,
        )


v1.register.check_plugin(
    name="mcafee_webgateway_misc",
    service_name="Web gateway miscellaneous",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_function=check_mcafee_webgateway_misc,
    discovery_function=discovery_mcafee_webgateway_misc,
    check_default_parameters={},
)
