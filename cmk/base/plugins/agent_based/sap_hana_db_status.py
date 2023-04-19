#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana

MAP_DB_STATUS = {"OK": State.OK, "WARNING": State.WARN}


def parse_sap_hana_db_status(string_table: StringTable) -> Dict[str, str]:
    return {
        sid_instance: lines[0][0] if lines else ""
        for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items()
    }


register.agent_section(
    name="sap_hana_db_status",
    parse_function=parse_sap_hana_db_status,
)


def discovery_sap_hana_db_status(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_db_status(item: str, section: Dict[str, str]) -> CheckResult:
    db_status = section.get(item)

    if not db_status:
        raise IgnoreResultsError("Login into database failed.")

    yield Result(state=MAP_DB_STATUS.get(db_status, State.CRIT), summary=db_status)


register.check_plugin(
    name="sap_hana_db_status",
    service_name="SAP HANA Database Status %s",
    discovery_function=discovery_sap_hana_db_status,
    check_function=check_sap_hana_db_status,
)
