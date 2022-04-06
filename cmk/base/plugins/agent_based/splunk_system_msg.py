#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass
class SplunkMessage:
    name: str
    severity: str
    server: str
    timeCreated_iso: str
    message: str


Section = list[SplunkMessage]


def parse(string_table: StringTable) -> Section:
    parsed = []
    for msg_list in string_table:
        try:
            name, severity, server, timeCreated_iso = msg_list[0:4]
            message = " ".join(msg_list[5:])

            parsed.append(SplunkMessage(name, severity, server, timeCreated_iso, message))

        except (IndexError, ValueError):
            pass
    return parsed


register.agent_section(name="splunk_system_msg", parse_function=parse)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No open messages")
        return

    data = section

    for msg in data:
        state = _handle_severity(msg.severity)
        summary = f"{msg.timeCreated_iso} - {msg.server} - {msg.message}"
        yield Result(state=state, summary=summary)


def _handle_severity(severity: str) -> State:
    severity_mapping = {
        "info": State.OK,
        "warn": State.WARN,
        "error": State.CRIT,
    }
    try:
        return severity_mapping[severity]
    except KeyError:
        return State.UNKNOWN


register.check_plugin(
    name="splunk_system_msg",
    service_name="Splunk System Messages",
    discovery_function=discovery,
    check_function=check,
)
