#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.mkeventd._openapi.commands import filter_historical_events_table
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException

from .endpoint_family import HISTORICAL_EVENTS_FAMILY
from .models.response_models import HistoricalEventModel
from .permissions import PERMISSIONS


def show_historical_event_unstable(
    api_context: ApiContext,
    event_id: Annotated[
        int,
        PathParam(description="An existing event ID.", example="42"),
    ],
    site_id: Annotated[
        SiteId,
        QueryParam(
            description="The ID of the site the historical event belongs to.",
            example="prod",
        ),
    ],
) -> HistoricalEventModel:
    """Show a historical event"""
    if not (
        event_history := (
            filter_historical_events_table(event_ids=[event_id]).fetchall(
                sites.live(), True, [site_id]
            )
        )
    ):
        raise RestAPIRequestGeneralException(
            status=404,
            title=f"Event ID {event_id} not found",
            detail=f"We could not find any historical event with the given event ID on site '{site_id}'.",
        )

    return HistoricalEventModel.historical_event_from_internal(event_history=tuple(event_history))


ENDPOINT_SHOW_HISTORICAL_EVENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("historical_event", "{event_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HISTORICAL_EVENTS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_historical_event_unstable)},
)
