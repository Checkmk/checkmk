#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Annotated

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.mkeventd._openapi.commands import (
    filter_event_table,
    update_and_acknowledge,
)
from cmk.gui.mkeventd._openapi.current_events.endpoint_family import CURRENT_EVENTS_FAMILY
from cmk.gui.openapi.framework._types import PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException

from .models.request_models import UpdateAndAcknowledeEventSiteIDRequiredModel
from .utils import UPDATE_AND_ACKNOWLEDGE_PERMISSIONS


def update_and_acknowledge_event(
    event_id: Annotated[
        int,
        PathParam(description="An existing event ID.", example="42"),
    ],
    body: UpdateAndAcknowledeEventSiteIDRequiredModel,
) -> None:
    """Update and acknowledge an event"""
    user.need_permission("mkeventd.update")
    user.need_permission("mkeventd.update_comment")
    user.need_permission("mkeventd.update_contact")
    query = filter_event_table(event_id=event_id)

    results = update_and_acknowledge(
        connection=sites.live(),
        change_comment=body.change_comment if isinstance(body.change_comment, str) else "",
        change_contact=body.change_contact if isinstance(body.change_contact, str) else "",
        query=query,
        new_phase=body.phase,
        site_id=body.site_id,
    )

    if not results:
        raise RestAPIRequestGeneralException(
            status=404,
            title="The requested event was not found",
            detail=f"Could not find event with id {event_id}.",
        )


ENDPOINT_UPDATE_AND_ACK_EVENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("event_console", "{event_id}", "update_and_acknowledge"),
        link_relation="cmk/update_and_acknowledge",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=UPDATE_AND_ACKNOWLEDGE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_and_acknowledge_event)},
)
