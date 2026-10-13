#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY

TITLES = [
    [
        "Temperature",
        "Voltage",
        "Power Supplies",
        "Cooling",
        "Other Modules",
        "UPS",
        "Bridge",
        "RAID",
    ],
    [
        "AV DAT",
        "AV Engine",
        "Spam DAT",
        "Spam Engine",
        "Config Antirelay",
        "Encryption",
        "SMTP",
        "POP3",
        "EPO",
        "TQM-Server",
        "GTI Message",
        "GTM Feedback",
        "GTI File",
        "RBL",
        "R-Syslog",
        "Remote Syslog",
        "LDAP",
        "Remove LDAP",
        "SNMPd",
        "Remove DNS",
        "NTP",
    ],
    ["WEBMC", "Eventhandler", "SMTP Retryer", "Spam Updater", "Postgres", "RMD Merge"],
]


def parse_mcafee_emailgateway_entities(
    string_table: Sequence[StringTable],
) -> Mapping[str, str] | None:
    return (
        {
            k: v
            for subtable, services in zip(string_table, TITLES, strict=False)
            for k, v in zip(services, subtable[0], strict=False)
        }
        if all(string_table)
        else None
    )


def discover_mcafee_emailgateway_entities(section: Mapping[str, str]) -> DiscoveryResult:
    for title, dev_state in section.items():
        if dev_state not in ("10", "11"):
            yield Service(item=title)


def check_mcafee_emailgateway_entities(item: str, section: Mapping[str, str]) -> CheckResult:
    map_states = {
        "0": (State.OK, "healthy"),
        "1": (State.WARN, "operational but requires attention"),
        "2": (State.WARN, "requires attention"),
        "3": (State.WARN, "end of life reached"),
        "4": (State.WARN, "near end of life"),
        "5": (State.CRIT, "corrupt dats"),
        "6": (State.CRIT, "corrupt configuration"),
        "7": (State.CRIT, "requires immediate attention"),
        "8": (State.CRIT, "critical"),
        "9": (State.UNKNOWN, "unknown state"),
        "10": (State.WARN, "disabled"),
        "11": (State.WARN, "not applicable"),
    }

    if item in section:
        state, state_readable = map_states[section[item]]
        yield Result(state=state, summary=f"Status: {state_readable}")


snmp_section_mcafee_emailgateway_entities = SNMPSection(
    name="mcafee_emailgateway_entities",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1230.2.4.1.2.3.2",
            oids=["1", "2", "3", "4", "5", "6", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1230.2.4.1.2.3.4",
            oids=[
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "12",
                "13",
                "14",
                "15",
                "16",
                "17",
                "18",
                "19",
                "20",
                "21",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1230.2.4.1.2.3.5",
            oids=["1", "2", "3", "4", "5", "6"],
        ),
    ],
    parse_function=parse_mcafee_emailgateway_entities,
)


check_plugin_mcafee_emailgateway_entities = CheckPlugin(
    name="mcafee_emailgateway_entities",
    service_name="Entity %s",
    discovery_function=discover_mcafee_emailgateway_entities,
    check_function=check_mcafee_emailgateway_entities,
)
