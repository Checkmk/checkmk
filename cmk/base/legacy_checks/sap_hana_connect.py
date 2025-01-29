#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Callable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.lib import sap_hana

check_info = {}

_SAP_HANA_CONNECT_STATE_MAP: Mapping[str, tuple[int, Callable[[str], bool]]] = {
    "Worker: OK": (0, lambda inp: inp == "0"),
    "Standby: OK": (0, lambda inp: inp == "1"),
    "No connect": (2, lambda inp: inp not in ("0", "1")),
}


def parse_sap_hana_connect(string_table):
    parsed: dict[str, dict] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst = parsed.setdefault(
            sid_instance,
            {
                "server_node": "not found",
                "driver_version": "not found",
                "timestamp": "not found",
                "cmk_state": 3,
                "message": " ".join(lines[0]),
            },
        )
        for elem in lines[0]:
            if "retcode" in elem:
                retcode = elem.split(":")[1].lstrip()
                for k, (state, evaluator) in _SAP_HANA_CONNECT_STATE_MAP.items():
                    if evaluator(retcode):
                        inst["cmk_state"] = state
                        inst["message"] = k
            if "Driver version" in elem:
                inst["driver_version"] = elem.split("Driver version")[1].lstrip()
            if "Connect string:" in elem:
                if (search := re.search("SERVERNODE=(.*?),(SERVERDB|UID|PWD)", elem)) is None:
                    raise ValueError(elem)
                inst["server_node"] = search.group(1)
            if "Select now()" in elem:
                if (search := re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", elem)) is None:
                    raise ValueError(elem)
                inst["timestamp"] = search.group()

    return parsed


def check_sap_hana_connect(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    state = data["cmk_state"]
    message = "{}\nODBC Driver Version: {}, Server Node: {}, Timestamp: {}".format(
        data["message"],
        data["driver_version"],
        data["server_node"],
        data["timestamp"],
    )
    yield state, message


def discover_sap_hana_connect(section):
    yield from ((item, {}) for item in section)


check_info["sap_hana_connect"] = LegacyCheckDefinition(
    name="sap_hana_connect",
    parse_function=parse_sap_hana_connect,
    service_name="SAP HANA CONNECT %s",
    discovery_function=discover_sap_hana_connect,
    check_function=check_sap_hana_connect,
)
