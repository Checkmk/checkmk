#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Final, Mapping

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana

SAP_HANA_REPL_STATUS_MAP: Final = {
    "0": (State.UNKNOWN, "unknown status from replication script", "state_unknown"),
    "10": (State.CRIT, "no system replication", "state_no_replication"),
    "11": (State.CRIT, "error", "state_error"),
    # "12" accuatly stands for "unknown replication status", but as per customer"s information
    # (see SUP-1436), this should be indicated as "passive" replication aka secondary SAP HANA node.
    "12": (State.OK, "passive", "state_replication_unknown"),
    "13": (State.WARN, "initializing", "state_initializing"),
    "14": (State.OK, "syncing", "state_syncing"),
    "15": (State.OK, "active", "state_active"),
}


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


register.agent_section(
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

    sys_repl_status = data["sys_repl_status"]
    state, state_readable, param_key = SAP_HANA_REPL_STATUS_MAP.get(
        sys_repl_status, (State.UNKNOWN, "unknown[%s]" % sys_repl_status, "state_unknown")
    )

    yield Result(
        state=params.get(param_key, state), summary="System replication: %s" % state_readable
    )


register.check_plugin(
    name="sap_hana_replication_status",
    service_name="SAP HANA Replication Status %s",
    discovery_function=discovery_sap_hana_replication_status,
    check_function=check_sap_hana_replication_status,
    check_ruleset_name="sap_hana_replication_status",
    check_default_parameters={},
)
