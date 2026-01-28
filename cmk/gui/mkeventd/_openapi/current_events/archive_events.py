#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Field

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.mkeventd._openapi.commands import (
    archive_events,
    filter_event_table,
)
from cmk.gui.mkeventd._openapi.current_events.endpoint_family import CURRENT_EVENTS_FAMILY
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from .models.request_models import FilterById, FilterByParams, FilterByQuery
from .utils import DEL_PERMISSION


def archive_events_with_filter(
    body: Annotated[
        FilterById | FilterByParams | FilterByQuery,
        Field(discriminator="filter_type"),
    ],
) -> None:
    """Archive events"""
    user.need_permission("mkeventd.delete")

    site_id: SiteId | None = None
    match body:
        case FilterByParams():
            filters = body.filters
            del_query = filter_event_table(
                host=filters.host if isinstance(filters.host, str) else None,
                state=filters.state if isinstance(filters.state, str) else None,
                application=filters.application if isinstance(filters.application, str) else None,
                phase=filters.phase if isinstance(filters.phase, str) else None,
            )

        case FilterById():
            del_query = filter_event_table(event_id=body.event_id)
            site_id = body.site_id

        case FilterByQuery():
            del_query = filter_event_table(query=body.query)

        case _:
            assert_never(body)

    archive_events(sites.live(), del_query, site_id)


ENDPOINT_ARCHIVE_CURRENT_EVENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("event_console", "delete"),
        link_relation=".../delete",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=DEL_PERMISSION),
    doc=EndpointDoc(family=CURRENT_EVENTS_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=archive_events_with_filter)},
)
