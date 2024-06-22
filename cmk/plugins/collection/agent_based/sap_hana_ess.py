#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import sap_hana


def parse_sap_hana_ess(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst_data: dict[str, str | int] = {}
        for line in lines:
            if len(line) < 2:
                continue

            key = line[0]
            if key == "started":
                try:
                    inst_data[key] = int(line[1])
                except ValueError:
                    pass
            else:
                inst_data[key] = line[1]
        section.setdefault(sid_instance, inst_data)
    return section


agent_section_sap_hana_ess = AgentSection(
    name="sap_hana_ess",
    parse_function=parse_sap_hana_ess,
)


def discovery_sap_hana_ess(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_ess(item: str, section: sap_hana.ParsedSection) -> CheckResult:
    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    active_state_name = data["active"]
    if active_state_name == "unknown":
        state = State.UNKNOWN
    elif active_state_name in ["false", "no"]:
        state = State.CRIT
    else:
        state = State.OK
    yield Result(state=state, summary="Active status: %s" % active_state_name)

    started_threads = data.get("started", 0)
    if started_threads is None or started_threads < 1:
        state = State.CRIT
    else:
        state = State.OK
    yield Result(state=state, summary="Started threads: %s" % started_threads)
    yield Metric("threads", started_threads)


check_plugin_sap_hana_ess = CheckPlugin(
    name="sap_hana_ess",
    service_name="SAP HANA ESS %s",
    discovery_function=discovery_sap_hana_ess,
    check_function=check_sap_hana_ess,
)
