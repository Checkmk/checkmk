#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Callable, Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.sap_hana import lib as sap_hana

_SAP_HANA_CONNECT_STATE_MAP: Mapping[str, tuple[State, Callable[[str], bool]]] = {
    "Worker: OK": (State.OK, lambda inp: inp == "0"),
    "Standby: OK": (State.OK, lambda inp: inp == "1"),
    "No connect": (State.CRIT, lambda inp: inp not in ("0", "1")),
}


class Instance(TypedDict):
    server_node: str
    driver_version: str
    timestamp: str
    cmk_state: State
    message: str


type Section = Mapping[str, Instance]


def parse_sap_hana_connect(string_table: StringTable) -> Section:
    parsed: dict[str, Instance] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst = parsed.setdefault(
            sid_instance,
            {
                "server_node": "not found",
                "driver_version": "not found",
                "timestamp": "not found",
                "cmk_state": State.UNKNOWN,
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


def check_sap_hana_connect(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    details = (
        f"ODBC Driver Version: {data['driver_version']}, "
        f"Server Node: {data['server_node']}, "
        f"Timestamp: {data['timestamp']}"
    )
    yield Result(state=data["cmk_state"], summary=data["message"], details=details)


def discover_sap_hana_connect(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_sap_hana_connect = AgentSection(
    name="sap_hana_connect",
    parse_function=parse_sap_hana_connect,
)


check_plugin_sap_hana_connect = CheckPlugin(
    name="sap_hana_connect",
    service_name="SAP HANA CONNECT %s",
    discovery_function=discover_sap_hana_connect,
    check_function=check_sap_hana_connect,
)
