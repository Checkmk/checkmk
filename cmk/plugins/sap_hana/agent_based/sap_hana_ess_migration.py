#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.sap_hana import lib as sap_hana


class StateInfo(TypedDict):
    cmk_state: State
    state_readable: str


# With reference to SQL sample output (see internal ticket SUP-253)
sap_hana_ess_migration_state_map: Mapping[str, StateInfo] = {
    "Done (error)": {"cmk_state": State.CRIT, "state_readable": "Done with errors."},
    "Installing": {"cmk_state": State.WARN, "state_readable": "Installation in progress."},
    "Done (okay)": {"cmk_state": State.OK, "state_readable": "Done without errors."},
}


class Instance(TypedDict):
    log: str
    timestamp: str


type Section = Mapping[str, Instance]


def parse_sap_hana_ess_migration(string_table: StringTable) -> Section:
    parsed: dict[str, Instance] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        if not lines:
            parsed[sid_instance] = {"log": "", "timestamp": "not available"}
            continue

        parsed.setdefault(sid_instance, {"log": " ".join(lines[0]), "timestamp": "not available"})

        for idx, elem in enumerate(lines[0]):
            try:
                timestamp = datetime.datetime.strptime(
                    elem + lines[0][idx + 1], "%Y-%m-%d%H:%M:%S.%f0"
                )
                timestamp_str = datetime.datetime.strftime(timestamp, "%Y-%m-%d %H:%M:%S")
                parsed[sid_instance]["timestamp"] = timestamp_str
            except (ValueError, IndexError):
                pass

    return parsed


def discover_sap_hana_ess_migration(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_ess_migration(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    if not data["log"]:
        raise IgnoreResultsError("Login into database failed.")

    states: StateInfo = {
        "cmk_state": State.UNKNOWN,
        "state_readable": f"Unknown [{data['log']}]",
    }
    for ident, info in sap_hana_ess_migration_state_map.items():
        if ident.lower() in data["log"].lower():
            states = info
    infotext = f"ESS State: {states['state_readable']} Timestamp: {data['timestamp']}"
    yield Result(state=states["cmk_state"], summary=infotext)


agent_section_sap_hana_ess_migration = AgentSection(
    name="sap_hana_ess_migration",
    parse_function=parse_sap_hana_ess_migration,
)


check_plugin_sap_hana_ess_migration = CheckPlugin(
    name="sap_hana_ess_migration",
    service_name="SAP HANA ESS Migration %s",
    discovery_function=discover_sap_hana_ess_migration,
    check_function=check_sap_hana_ess_migration,
)
