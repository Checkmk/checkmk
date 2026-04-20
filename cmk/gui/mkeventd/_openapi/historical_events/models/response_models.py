#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime

from cmk.gui.mkeventd._openapi.commands import (
    HistoricalPhaseType,
    SERVICE_LEVEL_INT_TO_NAME_MAP,
    ServiceLevelType,
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

# mypy: disable-error-code="mutable-override"


@api_model
class HistoricalEventHistoryEntryModel:
    """A single history entry representing the event state at a point in time."""

    action: str = api_field(
        description="The action that triggered this history entry.",
        example="NEW",
    )
    phase: HistoricalPhaseType = api_field(
        description="The phase of the event at the time of this history entry.",
        example="open",
    )
    state: str = api_field(
        description="The state of the event at the time of this history entry.",
        example="ok",
    )
    count: int = api_field(
        description="The number of occurrences of this event at the time of this history entry.",
        example=1,
    )
    text: str = api_field(
        description="The event message text at the time of this history entry.",
        example="Sample message text",
    )
    application: str = api_field(
        description="The syslog tag/application at the time of this history entry.",
        example="app_1",
    )
    service_level: ServiceLevelType | Literal["unknown"] = api_field(
        description="The service level at the time of this history entry.",
        example="gold",
    )
    comment: str = api_field(
        description="The event comment at the time of this history entry.",
        example="Example comment",
    )
    contact: str = api_field(
        description="The event contact information at the time of this history entry.",
        example="Mr Monitor",
    )
    timestamp: Annotated[dt.datetime, AwareDatetime] = api_field(
        description="The timestamp of the this event.",
        example="2017-11-09T17:32:28Z",
    )


@api_model
class HistoricalEventExtensionsModel:
    """Fields that are stable across all history entries for a given event."""

    site_id: str = api_field(
        description="The site id of the EC event.",
        example="heute",
    )
    host: str = api_field(
        description="The host name associated with the event.",
        example="host_1",
    )
    rule_id: str = api_field(
        description="The ID of the rule that matched this event.",
        example="rule_1",
    )
    ipaddress: str = api_field(
        description="The IP address where the event originated.",
        example="127.0.0.1",
    )
    facility: SyslogFacilityType | Literal["unknown"] = api_field(
        description="The syslog facility.",
        example="kern",
    )
    priority: SyslogPriorityType | Literal["unknown"] = api_field(
        description="The syslog priority.",
        example="warning",
    )
    history: list[HistoricalEventHistoryEntryModel] = api_field(
        description="The history of this event, one entry per recorded action.",
        example=[
            {
                "action": "NEW",
                "phase": "open",
                "state": "ok",
                "count": 1,
                "timestamp": "2026-04-09T16:12:12Z",
                "text": "Sample message text.",
                "application": "app_1",
                "service_level": "gold",
                "comment": "",
                "contact": "Mr Monitor",
            }
        ],
    )


@api_model
class HistoricalEventModel(DomainObjectModel):
    domainType: Literal["historical_event"] = api_field(
        description="The domain type of the object.",
    )

    extensions: HistoricalEventExtensionsModel = api_field(
        description="The details of the historical event.",
    )

    @classmethod
    def historical_collection_from_internal(
        cls,
        historical_event_collection: tuple[ResultRow, ...],
    ) -> list[Self]:
        grouped: dict[int, list[ResultRow]] = {}
        for row in historical_event_collection:
            grouped.setdefault(row["event_id"], []).append(row)
        return [cls.historical_event_from_internal(tuple(rows)) for rows in grouped.values()]

    @classmethod
    def historical_event_from_internal(cls, event_history: tuple[ResultRow, ...]) -> Self:
        sorted_history = sorted(event_history, key=lambda e: e["history_time"])
        first_row = sorted_history[0]

        return cls(
            domainType="historical_event",
            id=str(first_row["event_id"]),
            title="Historical Event",
            extensions=HistoricalEventExtensionsModel(
                site_id=first_row["site"],
                host=first_row["event_host"],
                rule_id=first_row["event_rule_id"],
                ipaddress=first_row["event_ipaddress"],
                facility=SYSLOG_FACILITY_INT_TO_NAME_MAP.get(
                    first_row["event_facility"], "unknown"
                ),
                priority=SYSLOG_PRIORITY_INT_TO_NAME_MAP.get(
                    first_row["event_priority"], "unknown"
                ),
                history=[
                    HistoricalEventHistoryEntryModel(
                        action=event["history_what"],
                        phase=event["event_phase"],
                        state=STATE_INT_TO_NAME_MAP[event["event_state"]],
                        count=event["event_count"],
                        text=event["event_text"],
                        application=event["event_application"],
                        service_level=SERVICE_LEVEL_INT_TO_NAME_MAP.get(
                            event["event_sl"], "unknown"
                        ),
                        comment=event["event_comment"],
                        contact=event["event_contact"],
                        timestamp=dt.datetime.fromtimestamp(event["history_time"], tz=dt.UTC),
                    )
                    for event in sorted_history
                ],
            ),
            links=generate_links(
                domain_type="historical_event",
                identifier=str(first_row["event_id"]),
                deletable=False,
                editable=False,
            ),
        )
