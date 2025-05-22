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


def format_alert(alert):
    s = alert["name"]
    if alert.get("acknowledge"):
        s += f", acknowledged by {alert['acknowledger']}"
    if alert.get("suppress"):
        s += f", suppressed by {alert['suppressor']}"
    return s


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
        yield Result(state=State.OK, summary="No alerts present")
    else:
        alerts = [dict(alert) for alert in section]
        unhandled_alerts = [
            alert for alert in alerts if not (alert.get("acknowledge") or alert.get("suppress"))
        ]
        handled_alerts = [
            alert for alert in alerts if alert.get("acknowledge") or alert.get("suppress")
        ]
        details = "\n".join(format_alert(alert) for alert in unhandled_alerts + handled_alerts)
        if unhandled_alerts:
            yield Result(
                state=State.CRIT, summary="Unhandled alerts present, see details", details=details
            )
        else:
            yield Result(
                state=State.OK,
                summary="Alerts present, but all acknowledged or suppressed, see details",
                details=details,
            )


check_plugin_netapp_ontap_status = CheckPlugin(
    name="netapp_ontap_status",
    service_name="Diagnosis Status",
    sections=["netapp_ontap_alerts"],
    discovery_function=discovery_netapp_ontap_status,
    check_function=check_netapp_ontap_status,
)
