#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.2.1 AP1
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.4.1 1
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.8.1
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.17.1 990625700
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.26.1 1
# .1.3.6.1.4.1.15983.1.1.4.2.1.1.27.1 3
# .1.3.6.1.4.1.15983.1.1.3.1.7.1.3.1 "00 0C E6 XX XX XX "
# .1.3.6.1.4.1.15983.1.1.3.1.7.1.5.1 1
# .1.3.6.1.4.1.15983.1.1.3.1.7.1.9.1 1


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, render, SNMPTree

check_info = {}


def parse_fortinet_controller_aps(string_table):
    map_oper_state = {
        "0": "unknown",
        "1": "enabled",
        "2": "disabled",
        "3": "no license",
        "4": "enabled WN license",
        "5": "power down",
    }

    map_availability = {
        "1": "power off",
        "2": "offline",
        "3": "online",
        "4": "failed",
        "5": "in test",
        "6": "not installed",
    }

    parsed = {}
    ap_table, client_table = string_table
    for descr, id_, location, uptime_str, oper_state, availability in ap_table:
        try:
            uptime = int(uptime_str)
        except ValueError:
            uptime = None
        parsed.setdefault(
            id_,
            {
                "descr": descr,
                "location": location,
                "uptime": uptime,
                "operational": map_oper_state[oper_state],
                "availability": map_availability[availability],
                "clients_count_24": 0,
                "clients_count_5": 0,
            },
        )

    for client, id_ in client_table:
        inst = parsed.get(id_)
        if inst is None:
            continue
        if client == "1":
            inst["clients_count_24"] += 1
        elif client == "2":
            inst["clients_count_5"] += 1
    return parsed


def inventory_fortinet_controller_aps(parsed):
    for key, values in parsed.items():
        if values["availability"] != "not installed":
            yield key, {}


def check_fortinet_controller_aps(item, params, parsed):
    data = parsed.get(item)
    if data is None:
        return

    oper_state = data["operational"]
    state = 0
    if oper_state == "unknown":
        state = 3
    elif oper_state in ["disabled", "no license", "power down"]:
        state = 1
    yield state, "[{}] Operational: {}".format(data["descr"], oper_state)

    avail_state = data["availability"]
    state = 0
    if avail_state == "failed":
        state = 2
    elif avail_state in ["power off", "offline", "in test", "not installed"]:
        state = 1
    yield state, "Availability: %s" % avail_state

    client_count_24 = data["clients_count_24"]
    client_count_5 = data["clients_count_5"]
    yield (
        0,
        f"Connected clients (2,4 ghz/5 ghz): {client_count_24}/{client_count_5}",
        [
            ("5ghz_clients", client_count_5),
            ("24ghz_clients", client_count_24),
        ],
    )

    uptime = data["uptime"]
    if uptime:
        yield 0, "Up since %s" % render.datetime(uptime), [("uptime", uptime)]

    location = data.get("location")
    if location:
        yield 0, "Located at %s" % location


check_info["fortinet_controller_aps"] = LegacyCheckDefinition(
    name="fortinet_controller_aps",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.15983"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.15983.1.1.4.2.1.1",
            oids=["2", "4", "8", "17", "26", "27"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.15983.1.1.3.1.7.1",
            oids=["5", "9"],
        ),
    ],
    parse_function=parse_fortinet_controller_aps,
    service_name="AP %s",
    discovery_function=inventory_fortinet_controller_aps,
    check_function=check_fortinet_controller_aps,
)
