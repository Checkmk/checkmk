#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal, Self

from pydantic import model_validator

from cmk.ccc.site import SiteId
from cmk.gui.mkeventd._openapi.commands import PhaseType, ServiceStateType
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import query_expression_validator
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables.eventconsoleevents import Eventconsoleevents

type EventConsoleEventsQuery = Annotated[
    QueryExpression,
    query_expression_validator(Eventconsoleevents),
]

query_events_console_field: EventConsoleEventsQuery = api_field(
    description="A Livestatus query expression to filter events. "
    "Accepts a JSON object with 'op', 'left', and 'right' for binary expressions, "
    "or 'op' and 'expr' for logical AND/OR expressions.",
    example='{"op": "=", "left": "event_host", "right": "myhost"}',
)


@api_model
class UpdateAndAcknowledgeEventModel:
    phase: PhaseType = api_field(
        example="ack",
        description="To change the phase of an event",
        default="ack",
    )
    change_comment: str | None = api_field(
        example="Comment now acked",
        description="Event comment.",
        default=None,
    )
    change_contact: str | None = api_field(
        example="Mr Monitor",
        description="Contact information.",
        default=None,
    )


@api_model
class UpdateAndAcknowledeEventSiteIDRequiredModel(UpdateAndAcknowledgeEventModel):
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
    ] = api_field(
        description="An existing site id",
        example="heute",
    )


@api_model
class ChangeEventStateModel:
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
    ] = api_field(
        description="An existing site id",
        example="heute",
    )
    new_state: ServiceStateType = api_field(
        description="The new state to set for the event.",
        example="ack",
    )


@api_model
class UpdateAndAcknowledgeMultipleBaseModel(UpdateAndAcknowledgeEventModel):
    site_id: (
        Annotated[
            SiteId,
            TypedPlainValidator(str, SiteIdConverter.should_exist),
        ]
        | None
    ) = api_field(
        description="An existing site id",
        example="heute",
        default=None,
    )


@api_model
class UpdateAndAcknowledgeWithQuery(UpdateAndAcknowledgeMultipleBaseModel):
    filter_type: Literal["query"] = api_field(
        example="all",
        description="The way you would like to filter events.",
    )
    query: EventConsoleEventsQuery = query_events_console_field


@api_model
class FilterParamsUpdateAndAcknowledge:
    state: ServiceStateType | None = api_field(
        description="The state of the event.",
        example="critical",
        default=None,
    )

    host: str | None = api_field(
        description="The host name of the event.",
        example="test_host",
        default=None,
    )

    application: str | None = api_field(
        description="The application name of the event.",
        example="my_app",
        default=None,
    )

    @model_validator(mode="after")
    def verify_at_least_one(self) -> Self:
        if not any((self.state, self.host, self.application)):
            raise ValueError(
                "At least one of the following parameters should be provided: state, host, application"
            )
        return self


@api_model
class UpdateAndAcknowledgeWithParams(UpdateAndAcknowledgeMultipleBaseModel):
    filter_type: Literal["params"] = api_field(
        example="all",
        description="The way you would like to filter events.",
    )

    filters: FilterParamsUpdateAndAcknowledge = api_field(
        description="Filtering parameters for events.",
        example={
            "host": "test_host",
            "state": "critical",
            "application": "my_app",
        },
    )


@api_model
class UpdateAndAcknowledgeAllModel(UpdateAndAcknowledgeMultipleBaseModel):
    filter_type: Literal["all"] = api_field(
        example="all",
        description="The way you would like to filter events.",
    )


@api_model
class FilterParams:
    state: ServiceStateType | None = api_field(
        description="The state of the event.",
        example="critical",
        default=None,
    )
    host: str | None = api_field(
        description="The host name of the event.",
        example="test_host",
        default=None,
    )
    phase: PhaseType | None = api_field(
        description="The phase of the event.",
        example="ack",
        default=None,
    )
    application: str | None = api_field(
        description="The application name of the event.",
        example="my_app",
        default=None,
    )

    @model_validator(mode="after")
    def verify_at_least_one(self) -> Self:
        if not any(
            {
                isinstance(self.state, str),
                isinstance(self.host, str),
                isinstance(self.phase, str),
                isinstance(self.application, str),
            }
        ):
            raise ValueError(
                "At least one of the following parameters should be provided: state, host, phase, application"
            )
        return self


@api_model
class ChangeStateFilterModel:
    site_id: (
        Annotated[
            SiteId,
            TypedPlainValidator(str, SiteIdConverter.should_exist),
        ]
        | None
    ) = api_field(
        description="An existing site id",
        example="heute",
        default=None,
    )
    new_state: ServiceStateType = api_field(
        description="The new state to set for the event.",
        example="ack",
    )


@api_model
class ChangeStateWithQueryModel(ChangeStateFilterModel):
    filter_type: Literal["query"] = api_field(
        example="query",
        description="The way you would like to filter events.",
    )
    query: EventConsoleEventsQuery = query_events_console_field


@api_model
class ChangeStateWithParamsModel(ChangeStateFilterModel):
    filter_type: Literal["params"] = api_field(
        example="params",
        description="The way you would like to filter events.",
    )
    filters: FilterParams = api_field(
        description="Filtering parameters for events.",
        example={
            "host": "test_host",
            "state": "critical",
            "application": "my_app",
        },
    )


@api_model
class FilterById:
    filter_type: Literal["by_id"] = api_field(
        example="by_id",
        description="The way you would like to filter events.",
    )
    site_id: (
        Annotated[
            SiteId,
            TypedPlainValidator(str, SiteIdConverter.should_exist),
        ]
        | None
    ) = api_field(
        description="An existing site id",
        example="heute",
        default=None,
    )
    event_id: int = api_field(
        description="The event console event ID.",
        example=1,
    )


@api_model
class FilterByQuery:
    filter_type: Literal["query"] = api_field(
        example="query",
        description="The way you would like to filter events.",
    )
    query: EventConsoleEventsQuery = query_events_console_field


@api_model
class FilterByParams:
    filter_type: Literal["params"] = api_field(
        example="params",
        description="The way you would like to filter events.",
    )
    filters: FilterParams = api_field(
        description="Filtering parameters for events.",
        example={
            "host": "test_host",
            "state": "critical",
            "application": "my_app",
        },
    )
