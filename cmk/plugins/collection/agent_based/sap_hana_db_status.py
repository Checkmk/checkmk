#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.lib import sap_hana

SectionDBStatus = Mapping[str, str]

MAP_DB_STATUS = {"OK": State.OK, "WARNING": State.WARN}


def parse_sap_hana_db_status(string_table: StringTable) -> SectionDBStatus:
    return {
        sid_instance: lines[0][0] if lines else ""
        for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items()
    }


agent_section_sap_hana_db_status = AgentSection(
    name="sap_hana_db_status",
    parse_function=parse_sap_hana_db_status,
)


def discover_sap_hana_db_status(
    section_sap_hana_db_status: SectionDBStatus | None,
    section_sap_hana_replication_status: sap_hana.ParsedSection | None,
) -> DiscoveryResult:
    if not section_sap_hana_db_status:
        return
    for item in section_sap_hana_db_status:
        yield Service(item=item)


def check_sap_hana_db_status(
    item: str,
    section_sap_hana_db_status: SectionDBStatus | None,
    section_sap_hana_replication_status: sap_hana.ParsedSection | None,
) -> CheckResult:
    if section_sap_hana_db_status is None:
        return

    db_status = section_sap_hana_db_status.get(item)

    if not db_status:
        raise IgnoreResultsError("Login into database failed.")

    db_state = MAP_DB_STATUS.get(db_status, State.CRIT)
    repl_state = (
        None
        if section_sap_hana_replication_status is None
        else section_sap_hana_replication_status.get(item, {}).get("sys_repl_status")
    )

    if (
        db_state is State.CRIT
        and repl_state is not None
        and sap_hana.get_replication_state(repl_state)[1] == "passive"
    ):
        yield Result(state=State.OK, summary="System is in passive mode")
        return

    yield Result(state=MAP_DB_STATUS.get(db_status, State.CRIT), summary=db_status)


check_plugin_sap_hana_db_status = CheckPlugin(
    name="sap_hana_db_status",
    service_name="SAP HANA Database Status %s",
    sections=["sap_hana_db_status", "sap_hana_replication_status"],
    discovery_function=discover_sap_hana_db_status,
    check_function=check_sap_hana_db_status,
)
