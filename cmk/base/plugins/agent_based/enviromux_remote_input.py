#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Mapping, NamedTuple

from .agent_based_api.v1 import (
    all_of,
    exists,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class InputStatus(Enum):
    notconnected = 0
    normal = 1
    prealert = 2
    alert = 3
    acknowledged = 4
    dismissed = 5
    disconnected = 6


class InputValue(Enum):
    closed = 0
    open = 1


class RemoteInput(NamedTuple):
    value: InputValue
    status: InputStatus
    normal_value: InputValue


Section = Mapping[str, RemoteInput]

input_status_mapping = {
    InputStatus.normal: State.OK,
    InputStatus.prealert: State.CRIT,
    InputStatus.alert: State.CRIT,
    InputStatus.acknowledged: State.WARN,
    InputStatus.dismissed: State.WARN,
    InputStatus.disconnected: State.CRIT,
}


def parse_enviromux_remote_input(string_table: StringTable) -> Section:
    section = {}

    for remote_input_data in string_table:
        index, desc, value, status, normal_value = remote_input_data

        remote_input = RemoteInput(
            value=InputValue(int(value)),
            status=InputStatus(int(status)),
            normal_value=InputValue(int(normal_value)),
        )

        section[f"{desc} {index}"] = remote_input

    return section


register.snmp_section(
    name="enviromux_remote_input",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.11"),
        exists(".1.3.6.1.4.1.3699.1.1.11.1.12.1.*"),
    ),
    parse_function=parse_enviromux_remote_input,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.11.1.12.1.1",
        oids=[
            "1",  # remoteInputEntry::remoteInputIndex
            "3",  # remoteInputEntry::remoteInputDescription
            "7",  # remoteInputEntry::remoteInputValue
            "8",  # remoteInputEntry::remoteInputStatus
            "9",  # remoteInputEntry::remoteInputNormalValue
        ],
    ),
)


def discover_enviromux_remote_input(section: Section) -> DiscoveryResult:
    for item, remote_input in section.items():
        if remote_input.status != InputStatus.notconnected:
            yield Service(item=item)


def check_enviromux_remote_input(item: str, section: Section) -> CheckResult:
    remote_input = section.get(item)
    if not remote_input:
        return

    value, normal_value = remote_input.value.name, remote_input.normal_value.name
    yield Result(state=State.OK, summary=f"Input value: {value}, Normal value: {normal_value}")

    if remote_input.value != remote_input.normal_value:
        yield Result(state=State.CRIT, summary="Input value different from normal")

    state = input_status_mapping[remote_input.status]
    yield Result(state=state, summary=f"Input status: {remote_input.status.name}")


register.check_plugin(
    name="enviromux_remote_input",
    service_name="Remote Input %s",
    discovery_function=discover_enviromux_remote_input,
    check_function=check_enviromux_remote_input,
)
