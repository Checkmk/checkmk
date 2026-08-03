#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Metric,
    OIDBytes,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringByteTable,
)


class IPSlaField(NamedTuple):
    description: str
    value: Any
    unit: str
    type_: str | None


Section = Mapping[str, Sequence[IPSlaField]]


def parse_cisco_ip_sla(string_table: Sequence[StringByteTable]) -> Section:
    precisions = {line[0]: "ms" if line[-1] == "1" else "us" for line in string_table[0]}

    rtt_types = {
        "1": "echo",
        "2": "path echo",
        "3": "file IO",
        "4": "script",
        "5": "UDP echo",
        "6": "TCP connect",
        "7": "HTTP",
        "8": "DNS",
        "9": "jitter",
        "10": "DLSw",
        "11": "DHCP",
        "12": "FTP",
        "13": "VoIP",
        "14": "RTP",
        "15": "LSP group",
        "16": "ICMP jitter",
        "17": "LSP ping",
        "18": "LSP trace",
        "19": "ethernet ping",
        "20": "ethernet jitter",
        "21": "LSP ping pseudowire",
    }

    states = {
        "1": "reset",
        "2": "orderly stop",
        "3": "immediate stop",
        "4": "pending",
        "5": "inactive",
        "6": "active",
        "7": "restart",
    }

    rtt_states = {
        "0": "other",
        "1": "ok",
        "2": "disconnected",
        "3": "over threshold",
        "4": "timeout",
        "5": "busy",
        "6": "not connected",
        "7": "dropped",
        "8": "sequence error",
        "9": "verify error",
        "10": "application specific error",
    }

    def to_ip_address(int_list: Sequence[int]) -> str:
        if len(int_list) == 4:
            return "%d.%d.%d.%d" % tuple(int_list)
        if len(int_list) == 6:
            return "%d:%d:%d:%d:%d:%d" % tuple(int_list)
        return ""

    # contains description, parse function, unit and type
    contents: Sequence[tuple[tuple[str, Callable[[Any], Any] | None, str, str | None], ...]] = [
        (  # rttMonEchoAdminEntry
            ("Target address", to_ip_address, "", None),
            ("Source address", to_ip_address, "", None),
            # rttMonEchoAdminPrecision is deliberatly dropped by zip below
        ),
        (  # rttMonCtrlAdminEntry
            ("Owner", None, "", None),
            ("Tag", None, "", None),
            ("RTT type", lambda x: rtt_types.get(x, "unknown"), "", "option"),
            ("Threshold", int, "ms", "option"),
        ),
        (  # rttMonCtrlOperEntry
            ("State", lambda x: states.get(x, "unknown"), "", "option"),
            ("Text", None, "", None),
            ("Connection lost occured", lambda x: "yes" if x == "1" else "no", "", "option"),
            ("Timeout occured", lambda x: "yes" if x == "1" else "no", "", "option"),
            (
                "Completion time over treshold occured",
                lambda x: "yes" if x == "1" else "no",
                "",
                "option",
            ),
        ),
        (  # rttMonLatestRttOperEntry
            ("Latest RTT completion time", int, "ms/us", "level"),
            ("Latest RTT state", lambda x: rtt_states.get(x, "unknown"), "", "option"),
        ),
    ]

    parsed: dict[str, list[IPSlaField]] = {}
    for content, entries in zip(contents, string_table):
        if not entries:
            continue

        for entry in entries:
            index, values = str(entry[0]), entry[1:]
            data = parsed.setdefault(index, [])
            for (description, parser, unit, type_), value in zip(content, values):
                if parser:
                    value = parser(value)
                if unit == "ms/us":
                    unit = precisions[index]
                data.append(IPSlaField(description, value, unit, type_))

    return parsed


def discover_cisco_ip_sla(section: Section) -> DiscoveryResult:
    for index in section:
        yield Service(item=index)


def check_cisco_ip_sla(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    for description, value, unit, type_ in data:
        if not value:
            continue

        state = State.OK
        infotext = f"{description}: {value} {unit}" if unit else f"{description}: {value}"

        param = params.get(description.lower().replace(" ", "_"))

        if type_ == "option":
            if param and param != value:
                state = State.WARN
                infotext += f" (expected {param})"
            yield Result(state=state, summary=infotext)
        elif type_ == "level":
            assert param is not None  # a default level has to exist
            warn, crit = param
            if value >= crit:
                state = State.CRIT
            elif value >= warn:
                state = State.WARN

            if state is not State.OK:
                infotext += f" (warn/crit at {warn}/{crit})"
            factor = 1e3 if unit == "ms" else 1e6
            yield Result(state=state, summary=infotext)
            yield Metric("rtt", value / factor, levels=(warn / factor, crit / factor))
        else:
            yield Result(state=state, summary=infotext)


snmp_section_cisco_ip_sla = SNMPSection(
    name="cisco_ip_sla",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        contains(".1.3.6.1.2.1.1.1.0", "ios"),
        exists(".1.3.6.1.4.1.9.9.42.1.2.2.1.37.*"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.42.1.2.2.1",
            oids=[OIDEnd(), OIDBytes("2"), OIDBytes("6"), "37"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.42.1.2.1.1",
            oids=[OIDEnd(), "2", "3", "4", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.42.1.2.9.1",
            oids=[OIDEnd(), "10", "2", "5", "6", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.42.1.2.10.1",
            oids=[OIDEnd(), "1", "2"],
        ),
    ],
    parse_function=parse_cisco_ip_sla,
)


check_plugin_cisco_ip_sla = CheckPlugin(
    name="cisco_ip_sla",
    service_name="Cisco IP SLA %s",
    discovery_function=discover_cisco_ip_sla,
    check_function=check_cisco_ip_sla,
    check_ruleset_name="cisco_ip_sla",
    check_default_parameters={
        "state": "active",
        "connection_lost_occured": "no",
        "timeout_occured": "no",
        "completion_time_over_treshold_occured": "no",
        "latest_rtt_completion_time": (250, 500),
        "latest_rtt_state": "ok",
    },
)
