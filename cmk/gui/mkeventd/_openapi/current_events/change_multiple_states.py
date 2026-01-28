#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.mkeventd._openapi.commands import (
    change_state,
    filter_event_table,
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

from .models.request_models import ChangeStateWithParamsModel, ChangeStateWithQueryModel
from .utils import CHANGE_STATE_PERMISSIONS


def change_multiple_event_states(
    body: Annotated[
        ChangeStateWithParamsModel | ChangeStateWithQueryModel,
        Discriminator("filter_type"),
    ],
) -> None:
    """Change multiple event states"""
    user.need_permission("mkeventd.changestate")

    match body:
        case ChangeStateWithParamsModel():
            filters = body.filters
            change_state_query = filter_event_table(
                host=filters.host,
                state=filters.state,
                application=filters.application,
                phase=filters.phase,
            )

        case ChangeStateWithQueryModel():
            change_state_query = filter_event_table(query=body.query)

        case _:
            assert_never(body)

    change_state(
        sites.live(),
        body.new_state,
        change_state_query,
        body.site_id,
    )


ENDPOINT_CHANGE_MULTIPLE_STATES_CURRENT_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("event_console", "change_state"),
        link_relation=".../collection_change_state",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=CHANGE_STATE_PERMISSIONS),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=change_multiple_event_states)},
    behavior=EndpointBehavior(update_config_generation=False),
)
