#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NamedTuple, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


class ConnectionState(NamedTuple):
    status: str
    description: str


class AccessPoint(NamedTuple):
    connection_state: ConnectionState
    station_count: int


Section = Mapping[str, AccessPoint]


_CONN_STATE_TO_READABLE: Mapping[str, tuple[str, str]] = {
    "0": (
        "other",
        "The WTP connection state is unknown.",
    ),
    "1": (
        "offLine",
        "The WTP is not connected.",
    ),
    "2": (
        "onLine",
        "The WTP is connected.",
    ),
    "3": (
        "downloadingImage",
        "The WTP is downloading software image from the AC on joining.",
    ),
    "4": (
        "connectedImage",
        "The AC is pushing software image to the connected WTP.",
    ),
    "5": (
        "standby",
        "The WTP is standby on the AC.",
    ),
}


def parse_fortigate_ap_connection(string_table: Sequence[StringTable]) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_fortigate_ap_connection([
    ... [["a"], ["b"]],
    ... [["1", "0"], ["2", "5"]],
    ... ]))
    {'a': AccessPoint(connection_state=ConnectionState(status='offLine', description='The WTP is not connected.'), station_count=0),
     'b': AccessPoint(connection_state=ConnectionState(status='onLine', description='The WTP is connected.'), station_count=5)}
    """
    return {
        wtp_name: AccessPoint(
            ConnectionState(*_CONN_STATE_TO_READABLE[connection_state]),
            int(station_count),
        )
        for (wtp_name,), (
            connection_state,
            station_count,
        ) in zip(*string_table)
    }


snmp_section_fortigate_ap_connection = SNMPSection(
    name="fortigate_ap_connection",
    parse_function=parse_fortigate_ap_connection,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.14.4.3.1",
            oids=[
                "3",  # fgWcWtpConfigWtpName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.14.4.4.1",
            oids=[
                "7",  # fgWcWtpSessionConnectionState
                "17",  # fgWcWtpSessionWtpStationCount
            ],
        ),
    ],
    detect=startswith(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.12356.101.1",
    ),
)


def discover_fortigate_ap_connection(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section if item)


class CheckParams(TypedDict):
    conn_state_to_mon_state: Mapping[str, int]


def check_fortigate_ap_connection(
    item: str,
    params: CheckParams,
    section: Section,
) -> CheckResult:
    if not (access_point := section.get(item)):
        return
    yield Result(
        state=State(params["conn_state_to_mon_state"][access_point.connection_state.status]),
        summary=f"State: {access_point.connection_state.status}",
        details=access_point.connection_state.description,
    )
    yield from check_levels_v1(
        access_point.station_count,
        metric_name="connections",
        label="Connected clients",
        render_func=str,
        boundaries=(
            0,
            None,
        ),
    )


check_plugin_fortigate_ap_connection = CheckPlugin(
    name="fortigate_ap_connection",
    service_name="AP %s Connection",
    discovery_function=discover_fortigate_ap_connection,
    check_default_parameters={
        "conn_state_to_mon_state": {
            "other": 3,
            "offLine": 1,
            "onLine": 0,
            "downloadingImage": 0,
            "connectedImage": 0,
            "standby": 0,
        },
    },
    check_function=check_fortigate_ap_connection,
)
