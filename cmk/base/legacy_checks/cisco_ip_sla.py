#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from collections.abc import Callable, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, exists, OIDBytes, OIDEnd, SNMPTree

check_info = {}


def parse_cisco_ip_sla(string_table):
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

    def to_ip_address(int_list):
        if len(int_list) == 4:
            return "%d.%d.%d.%d" % tuple(int_list)
        if len(int_list) == 6:
            return "%d:%d:%d:%d:%d:%d" % tuple(int_list)
        return ""

    # contains description, parse function, unit and type
    contents: Sequence[tuple[tuple[str, Callable | None, str, str | None], ...]] = [
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

    parsed: dict[str, list] = {}
    for content, entries in zip(contents, string_table):
        if not entries:
            continue

        for entry in entries:
            index, values = entry[0], entry[1:]
            data = parsed.setdefault(index, [])
            for (description, parser, unit, type_), value in zip(content, values):
                if parser:
                    value = parser(value)
                if unit == "ms/us":
                    unit = precisions[index]
                data.append((description, value, unit, type_))

    return parsed


def discover_cisco_ip_sla(parsed):
    for index in parsed:
        yield index, {}


def check_cisco_ip_sla(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    for description, value, unit, type_ in data:
        if not value:
            continue

        state = 0
        if unit:
            infotext = f"{description}: {value} {unit}"
        else:
            infotext = f"{description}: {value}"
        perfdata = []

        param = params.get(description.lower().replace(" ", "_"))

        if type_ == "option":
            if param and param != value:
                state = 1
                infotext += " (expected %s)" % param
        elif type_ == "level":
            warn, crit = param  # a default level hat to exist
            if value >= crit:
                state = 2
            elif value >= warn:
                state = 1

            if state:
                infotext += f" (warn/crit at {warn}/{crit})"
            factor = 1e3 if unit == "ms" else 1e6
            perfdata = [
                ("rtt", value / factor, warn / factor, crit / factor)
            ]  # fixed: true-division

        yield state, infotext, perfdata


check_info["cisco_ip_sla"] = LegacyCheckDefinition(
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
