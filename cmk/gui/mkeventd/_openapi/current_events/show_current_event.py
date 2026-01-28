#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.mkeventd._openapi.commands import (
    filter_event_table,
)
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException

from .endpoint_family import CURRENT_EVENTS_FAMILY
from .models.response_models import CurrentEventModel
from .utils import IGNORE_PERMISSIONS


def show_current_event_v1(
    event_id: Annotated[
        int,
        PathParam(description="An existing event ID.", example="42"),
    ],
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        QueryParam(
            description="The ID of the site the event belongs to.",
            example="prod",
        ),
    ],
) -> CurrentEventModel:
    """Show a current event"""
    try:
        current_event = filter_event_table(event_id=event_id).fetchone(
            sites.live(),
            True,
            site_id,
        )
    except ValueError:
        raise RestAPIRequestGeneralException(
            status=404,
            title="The requested event was not found",
            detail=f"Could not find event with id {event_id}.",
        )

    return CurrentEventModel.current_event_from_internal(current_event=current_event)


ENDPOINT_SHOW_CURRENT_EVENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("event_console", "{event_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=IGNORE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_current_event_v1)},
)
