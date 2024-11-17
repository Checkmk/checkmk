#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import DETECT_AUDIOCODES

_READABLE_STATUS = {
    "1": "active",
    "2": "notInService",
    "3": "notReady",
}

_READABLE_TYPE = {
    "0": "Server",
    "1": "User",
    "2": "Gateway",
}


@dataclass(frozen=True, kw_only=True)
class Attributes:
    index: int
    status: str
    type: str
    description: str | None
    name: str
    connect_status: str

    @property
    def item(self) -> str:
        return f"{self.index} {self.name}"


@dataclass(frozen=True, kw_only=True)
class ActiveCalls:
    calls_in: int | None
    calls_out: int | None


@dataclass(frozen=True, kw_only=True)
class IPGroup:
    attributes: Attributes
    active_calls: ActiveCalls


def parse_audiocodes_ipgroup(
    string_table: Sequence[StringTable],
) -> Mapping[str, IPGroup] | None:
    if not string_table or not string_table[0]:
        return None

    attributes_by_index = {info[0]: _parse_attributes(info) for info in string_table[0]}
    active_call_by_index = {
        index: ActiveCalls(
            calls_in=int(calls_in) if calls_in else None,
            calls_out=int(calls_out) if calls_out else None,
        )
        for index, calls_in, calls_out in string_table[1]
    }

    return {
        attributes.item: IPGroup(
            attributes=attributes,
            active_calls=active_call_by_index.get(
                index,
                ActiveCalls(calls_in=None, calls_out=None),
            ),
        )
        for index, attributes in attributes_by_index.items()
    }


snmp_section_audiocodes_ipgroup: SNMPSection = SNMPSection(
    name="audiocodes_ipgroup",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.3.1.1.23.21.1",
            oids=[
                "1",  # 0 ipGroup Index
                "2",  # 1 ipGroup status
                "5",  # 2 ipGroup Type
                "6",  # 3 ipGroup Description
                "31",  # 4 ipGroup Name
                "36",  # 5 connect status
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.3.1.1.2.1.1",
            oids=[
                OIDEnd(),
                "3",  # active calls in
                "4",  # active calls out
            ],
        ),
    ],
    parse_function=parse_audiocodes_ipgroup,
)


def discover_audiocodes_ipgroup(section: Mapping[str, IPGroup]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_audiocodes_ipgroup(item: str, section: Mapping[str, IPGroup]) -> CheckResult:
    if (ipgroup := section.get(item)) is None:
        return

    yield Result(
        state=_check_ipgroup_state(ipgroup),
        summary=f"Status: {ipgroup.attributes.status}",
        details=(
            f"IP Group Name: {ipgroup.attributes.name}, "
            f"Type: {ipgroup.attributes.type}, "
            f"IP Group Index: {ipgroup.attributes.index}, "
            f"Description: {ipgroup.attributes.description}, "
            f"Proxy set connectivity: {ipgroup.attributes.connect_status}"
        ),
    )
    yield from _check_ipgroup_calls_information(ipgroup.active_calls)


check_plugin_audiocodes_ipgroup = CheckPlugin(
    name="audiocodes_ipgroup",
    service_name="AudioCodes IPGroup %s",
    discovery_function=discover_audiocodes_ipgroup,
    check_function=check_audiocodes_ipgroup,
)


def _parse_attributes(attributes: Sequence[str]) -> Attributes:
    index, status, ipgroup_type, description, name, connect_status = attributes
    return Attributes(
        index=int(index),
        status=_READABLE_STATUS[status],
        type=_READABLE_TYPE[ipgroup_type],
        description=description if description else None,
        name=name,
        connect_status=connect_status,
    )


def _check_ipgroup_state(ipgroup: IPGroup) -> State:
    if ipgroup.attributes.status == "active" and (
        ipgroup.attributes.connect_status in ("Connected", "NA")
    ):
        return State.OK
    return State.CRIT


def _check_ipgroup_calls_information(
    active_calls: ActiveCalls,
) -> CheckResult:
    if active_calls.calls_in is not None:
        yield from check_levels(
            value=active_calls.calls_in,
            metric_name="audiocodes_ipgroup_active_calls_in",
            label="Active Calls In",
        )
    if active_calls.calls_out is not None:
        yield from check_levels(
            value=active_calls.calls_out,
            metric_name="audiocodes_ipgroup_active_calls_out",
            label="Active Calls Out",
        )
