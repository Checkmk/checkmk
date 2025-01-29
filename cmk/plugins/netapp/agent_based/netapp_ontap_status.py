#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

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
from cmk.plugins.netapp import models

Section = Sequence[models.AlertModel]

# <<<netapp_api_alerts:sep(0)>>>
# {
#     "name": "alert-name",
# }
# {
#     "name": "alert-name",
# }


def parse_netapp_api_status(string_table: StringTable) -> Section:
    return [
        alert for line in string_table for alert in [models.AlertModel.model_validate_json(line[0])]
    ]


agent_section_netapp_ontap_status = AgentSection(
    name="netapp_ontap_alerts",
    parse_function=parse_netapp_api_status,
)


def discovery_netapp_ontap_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_netapp_ontap_status(section: Section) -> CheckResult:
    """
    Status is considered OK if there are no alerts
    """

    if not section:
        yield Result(state=State.OK, summary="Status: OK")
    else:
        yield Result(state=State.CRIT, summary="Status: Alerts present")


check_plugin_netapp_ontap_status = CheckPlugin(
    name="netapp_ontap_status",
    service_name="Diagnosis Status",
    sections=["netapp_ontap_alerts"],
    discovery_function=discovery_netapp_ontap_status,
    check_function=check_netapp_ontap_status,
)
