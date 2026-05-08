#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.openapi.api_endpoints.downtime._utils import PERMISSIONS, serialize_single_downtime
from cmk.gui.openapi.api_endpoints.downtime.models.response_models import DowntimeObjectModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
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
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.downtimes import Downtimes

from ._family import DOWNTIME_FAMILY


def show_downtime_v1(
    downtime_id: Annotated[str, PathParam(description="The id of the downtime", example="54")],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(
            description="An existing site id",
            example="mysite",
        ),
    ],
    api_context: ApiContext,
) -> DowntimeObjectModel:
    """Show downtime"""
    live = sites.live()
    q = Query(
        columns=[
            Downtimes.id,
            Downtimes.host_name,
            Downtimes.service_description,
            Downtimes.is_service,
            Downtimes.author,
            Downtimes.start_time,
            Downtimes.end_time,
            Downtimes.recurring,
            Downtimes.comment,
            Downtimes.fixed,
            Downtimes.duration,
        ],
        filter_expr=Downtimes.id.op("=", downtime_id),
    )

    try:
        downtime = q.fetchone(live, True, site_id)
    except ValueError:
        raise ProblemException(
            status=404,
            title="The requested downtime was not found",
            detail=f"The downtime id {downtime_id} did not match any downtime",
        )

    return serialize_single_downtime(downtime, host_url=api_context.host_url)


ENDPOINT_SHOW_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("downtime", "{downtime_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=show_downtime_v1)},
)
