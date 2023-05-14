#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output


from cmk.base.check_api import any_of, contains, LegacyCheckDefinition, startswith
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree


def parse_cisco_asa_conn(info):
    parsed = {}
    for line in info[0]:
        parsed[line[0]] = [line[1]]
    for line in info[2]:
        parsed[line[0]].append(line[1])
        parsed[line[0]].append(line[2])
    for line in info[1]:
        parsed[line[0]].append(line[1])

    return parsed


def inventory_cisco_asa_conn(parsed):
    for key, values in parsed.items():
        if values[1] == "1" and len(values) == 4:
            yield (key, None)


def check_cisco_asa_conn(item, _no_params, parsed):
    translate_status = {
        "1": (0, "up"),
        "2": (2, "down"),
        "3": (3, "testing"),
        "4": (3, "unknown"),
        "5": (2, "dormant"),
        "6": (2, "not present"),
        "7": (2, "lower layer down"),
    }

    for key, values in parsed.items():
        if item == key:
            yield 0, "Name: %s" % values[0]

            try:
                ip_address = values[3]
            except IndexError:
                ip_address = None

            if ip_address:
                yield 0, "IP: %s" % ip_address
            else:  # CRIT if no IP is assigned
                yield 2, "IP: Not found!"

            state, state_readable = translate_status[values[2]]
            yield state, "Status: %s" % state_readable


check_info["cisco_asa_conn"] = LegacyCheckDefinition(
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firewall services"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
    ),
    parse_function=parse_cisco_asa_conn,
    discovery_function=inventory_cisco_asa_conn,
    check_function=check_cisco_asa_conn,
    service_name="Connection %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.4.20.1",
            oids=["2", "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[OIDEnd(), "7", "8"],
        ),
    ],
)
