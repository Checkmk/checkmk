#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Field

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.mkeventd._openapi.commands import (
    filter_event_table,
    PhaseType,
    update_and_acknowledge,
)
from cmk.gui.mkeventd._openapi.current_events.endpoint_family import CURRENT_EVENTS_FAMILY
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from .models.request_models import (
    UpdateAndAcknowledgeAllModel,
    UpdateAndAcknowledgeWithParams,
    UpdateAndAcknowledgeWithQuery,
)
from .utils import UPDATE_AND_ACKNOWLEDGE_PERMISSIONS


def update_and_acknowledge_multiple_events(
    body: Annotated[
        UpdateAndAcknowledgeAllModel
        | UpdateAndAcknowledgeWithParams
        | UpdateAndAcknowledgeWithQuery,
        Field(discriminator="filter_type"),
    ],
) -> None:
    """Update and acknowledge events"""
    user.need_permission("mkeventd.update")
    user.need_permission("mkeventd.update_comment")
    user.need_permission("mkeventd.update_contact")

    # Optimization - If the user wants to acknowledge events, filter for only open events
    # if the user wants to open events, filter for only acknowledged events
    filter_phase: PhaseType = "ack" if body.phase == "open" else "open"
    match body:
        case UpdateAndAcknowledgeAllModel():
            update_query = filter_event_table(phase=filter_phase)

        case UpdateAndAcknowledgeWithParams():
            update_query = filter_event_table(
                host=body.filters.host,
                state=body.filters.state,
                application=body.filters.application,
                phase=filter_phase,
            )
        case UpdateAndAcknowledgeWithQuery():
            update_query = filter_event_table(query=body.query, phase=filter_phase)

        case _:
            assert_never(body)

    update_and_acknowledge(
        connection=sites.live(),
        change_comment=body.change_comment if isinstance(body.change_comment, str) else "",
        change_contact=body.change_contact if isinstance(body.change_contact, str) else "",
        query=update_query,
        new_phase=body.phase,
        site_id=body.site_id,
    )


ENDPOINT_UPDATE_AND_ACK_MULTIPLE_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("event_console", "update_and_acknowledge"),
        link_relation=".../collection_update_and_acknowledge",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=UPDATE_AND_ACKNOWLEDGE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_and_acknowledge_multiple_events)},
    behavior=EndpointBehavior(update_config_generation=False),
)
