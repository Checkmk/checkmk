#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal, Self

from cmk.gui.mkeventd._openapi.commands import (
    PhaseType,
    SERVICE_LEVEL_INT_TO_NAME_MAP,
    ServiceLevelType,
    ServiceStateType,
    STATE_INT_TO_NAME_MAP,
    SYSLOG_FACILITY_INT_TO_NAME_MAP,
    SYSLOG_PRIORITY_INT_TO_NAME_MAP,
    SyslogFacilityType,
    SyslogPriorityType,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.livestatus_client.queries import ResultRow


@api_model
class CurrentEventFieldsModel:
    site_id: str = api_field(
        description="The site id of the EC event.",
        example="heute",
    )
    state: ServiceStateType = api_field(
        description="The state of the event.",
        example="ok",
    )
    service_level: ServiceLevelType | Literal["unknown"] = api_field(
        description="The service level for this event.",
        example="gold",
    )
    host: str = api_field(
        description="The host name associated with the event.",
        example="host_1",
    )
    rule_id: str = api_field(
        description="The ID of the rule.",
        example="rule_1",
    )
    application: str = api_field(
        description="The syslog tag/application this event originated from.",
        example="app_1",
    )
    comment: str = api_field(
        description="The event comment.",
        example="Example comment",
    )
    contact: str = api_field(
        description="The event contact information.",
        example="Mr Monitor",
    )
    ipaddress: str = api_field(
        description="The IP address where the event originated.",
        example="127.0.0.1",
    )
    facility: SyslogFacilityType = api_field(
        description="The syslog facility.",
        example="kern",
    )
    priority: SyslogPriorityType = api_field(
        description="The syslog priority.",
        example="warning",
    )
    phase: PhaseType = api_field(
        description="The phase of the event.",
        example="open",
    )
    last: float = api_field(
        description="The last timestamp of the event.",
        example="2017-11-09T17:32:28Z",
    )
    first: float = api_field(
        description="The first timestamp of the event.",
        example="2022-11-09T16:12:12Z",
    )
    count: int = api_field(
        description="The number of occurrences of this event within a period.",
        example=1,
    )
    text: str = api_field(
        example="Sample message text",
        description="The event message text",
    )


@api_model
class CurrentEventModel(DomainObjectModel):
    domainType: Literal["event_console"] = api_field(
        description="The domain type of the object.",
    )

    extensions: CurrentEventFieldsModel = api_field(
        description="The configuration attributes of a site.",
        example={
            "state": "ok",
            "service_level": "gold",
            "host": "host_1",
            "rule_id": "rule_1",
            "application": "app_1",
            "comment": "example_comment",
            "contact": "Mr Monitor",
            "ipaddress": "127.0.0.1",
            "facility": "kern",
            "priority": "warning",
            "phase": "open",
            "last": "Oct 21 2022 09:11:12",
            "first": "Oct 26 2022 07:51:25",
            "count": 1,
            "text": "Sample message text.",
        },
    )

    @classmethod
    def current_event_from_internal(cls, current_event: ResultRow) -> Self:
        return cls(
            domainType="event_console",
            id=str(current_event["event_id"]),
            title=current_event["event_text"],
            extensions=CurrentEventFieldsModel(
                site_id=current_event["site"],
                state=(STATE_INT_TO_NAME_MAP[current_event["event_state"]]),
                service_level=SERVICE_LEVEL_INT_TO_NAME_MAP.get(
                    current_event["event_sl"], "unknown"
                ),
                host=current_event["event_host"],
                rule_id=current_event["event_rule_id"],
                application=current_event["event_application"],
                comment=current_event["event_comment"],
                contact=current_event["event_contact"],
                ipaddress=current_event["event_ipaddress"],
                facility=SYSLOG_FACILITY_INT_TO_NAME_MAP[current_event["event_facility"]],
                priority=SYSLOG_PRIORITY_INT_TO_NAME_MAP[current_event["event_priority"]],
                phase=current_event["event_phase"],
                last=current_event["event_last"],
                first=current_event["event_first"],
                count=current_event["event_count"],
                text=current_event["event_text"],
            ),
            links=generate_links(
                domain_type="event_console",
                identifier=str(current_event["event_id"]),
                deletable=True,
                editable=False,
            ),
        )
