#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.mkeventd._openapi.commands import (
    change_state,
    filter_event_table,
)
from cmk.gui.mkeventd._openapi.current_events.endpoint_family import CURRENT_EVENTS_FAMILY
from cmk.gui.openapi.framework._types import PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException

from .models.request_models import ChangeEventStateModel
from .utils import CHANGE_STATE_PERMISSIONS


def change_event_state(
    event_id: Annotated[
        int,
        PathParam(description="An existing event ID.", example="42"),
    ],
    body: ChangeEventStateModel,
) -> None:
    """Change event state"""
    user.need_permission("mkeventd.changestate")
    query = filter_event_table(event_id=event_id)
    results = change_state(
        connection=sites.live(),
        state=body.new_state,
        query=query,
        site_id=SiteId(body.site_id),
    )
    if not results:
        raise RestAPIRequestGeneralException(
            status=404,
            title="The requested event was not found",
            detail=f"Could not find event with id {event_id}.",
        )


ENDPOINT_CHANGE_EVENT_STATE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("event_console", "{event_id}", "change_state"),
        link_relation="cmk/change_state",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=CHANGE_STATE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=change_event_state)},
    behavior=EndpointBehavior(update_config_generation=False),
)
