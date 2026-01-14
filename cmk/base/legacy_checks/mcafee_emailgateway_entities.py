#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY

check_info = {}

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


def parse_mcafee_emailgateway_entities(string_table):
    return (
        {
            k: v
            for subtable, services in zip(string_table, TITLES)
            for k, v in zip(services, subtable[0])
        }
        if all(string_table)
        else None
    )


def discover_mcafee_emailgateway_entities(parsed):
    for title, dev_state in parsed.items():
        if dev_state not in ["10", "11"]:
            yield title, {}


def check_mcafee_emailgateway_entities(item, params, parsed):
    map_states = {
        "0": (0, "healthy"),
        "1": (1, "operational but requires attention"),
        "2": (1, "requires attention"),
        "3": (1, "end of life reached"),
        "4": (1, "near end of life"),
        "5": (2, "corrupt dats"),
        "6": (2, "corrupt configuration"),
        "7": (2, "requires immediate attention"),
        "8": (2, "critical"),
        "9": (3, "unknown state"),
        "10": (1, "disabled"),
        "11": (1, "not applicable"),
    }

    if item in parsed:
        state, state_readable = map_states[parsed[item]]
        return state, "Status: %s" % state_readable
    return None


check_info["mcafee_emailgateway_entities"] = LegacyCheckDefinition(
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
    service_name="Entity %s",
    discovery_function=discover_mcafee_emailgateway_entities,
    check_function=check_mcafee_emailgateway_entities,
)
