#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Annotated, Literal

from livestatus import OnlySites

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.mkeventd._openapi.commands import (
    filter_event_table,
    PhaseType,
    ServiceStateType,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel
from cmk.gui.openapi.restful_objects.constructors import collection_href

from .endpoint_family import CURRENT_EVENTS_FAMILY
from .models.request_models import EventConsoleEventsQuery
from .models.response_models import CurrentEventModel
from .utils import IGNORE_PERMISSIONS


@api_model
class CurrentEventsCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["event_console"] = api_field(
        description="The domain type of the objects in the collection",
        example="event_console",
    )
    value: list[CurrentEventModel] = api_field(
        description="A list of current event objects.",
        example=[],
    )


def list_current_events_v1(
    api_context: ApiContext,
    site_id: Annotated[
        SiteId | None,
        QueryParam(
            description="The ID of the site the event belongs to.",
            example="prod",
        ),
    ] = None,
    host: Annotated[
        str | None,
        QueryParam(
            description="The host name of the event.",
            example="host1",
        ),
    ] = None,
    application: Annotated[
        str | None,
        QueryParam(
            description="The application name of the event.",
            example="app1",
        ),
    ] = None,
    state: Annotated[
        ServiceStateType | None,
        QueryParam(
            description="The state of the event.",
            example="ok",
        ),
    ] = None,
    phase: Annotated[
        PhaseType | None,
        QueryParam(
            description="The phase of the event.",
            example="ack",
        ),
    ] = None,
    query: Annotated[
        EventConsoleEventsQuery | None,
        QueryParam(
            description=(
                "A Livestatus query expression to filter events. "
                "Accepts a JSON object with 'op', 'left', and 'right' for binary expressions, "
                "or 'op' and 'expr' for logical AND/OR expressions."
            ),
            example='{"op": "=", "left": "event_host", "right": "myhost"}',
        ),
    ] = None,
) -> CurrentEventsCollectionModel:
    """Show events"""

    q = filter_event_table(
        state=state,
        application=application,
        host=host,
        phase=phase,
        query=query,
    )

    _site_id: OnlySites = [site_id] if site_id is not None else None

    return CurrentEventsCollectionModel(
        id="event_console",
        domainType="event_console",
        value=[
            CurrentEventModel.current_event_from_internal(event)
            for event in q.fetchall(sites.live(), True, _site_id)
        ],
        links=[],
        extensions={},
    )


ENDPOINT_LIST_CURRENT_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("event_console"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=IGNORE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_current_events_v1)},
)
