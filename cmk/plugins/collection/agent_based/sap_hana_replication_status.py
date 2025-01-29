#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    StringTable,
)
from cmk.plugins.lib import sap_hana


def parse_sap_hana_replication_status(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst = {}
        for line in lines:
            if line[0].lower() == "mode:":
                inst["mode"] = line[1]
            elif line[0].lower() in ["systemreplicationstatus:", "returncode:"]:
                inst["sys_repl_status"] = line[1]
        section.setdefault(sid_instance, inst)

    return section


agent_section_sap_hana_replication_status = AgentSection(
    name="sap_hana_replication_status",
    parse_function=parse_sap_hana_replication_status,
)


def discovery_sap_hana_replication_status(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for sid_instance, data in section.items():
        if not data or (
            data["sys_repl_status"] != "10"
            and (
                data.get("mode", "").lower() == "primary" or data.get("mode", "").lower() == "sync"
            )
        ):
            yield Service(item=sid_instance)


def check_sap_hana_replication_status(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:
    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    state, state_readable, param_key = sap_hana.get_replication_state(data["sys_repl_status"])

    yield Result(
        state=params.get(param_key, state), summary="System replication: %s" % state_readable
    )


check_plugin_sap_hana_replication_status = CheckPlugin(
    name="sap_hana_replication_status",
    service_name="SAP HANA Replication Status %s",
    discovery_function=discovery_sap_hana_replication_status,
    check_function=check_sap_hana_replication_status,
    check_ruleset_name="sap_hana_replication_status",
    check_default_parameters={},
)
