#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.openapi.api_endpoints.downtime._utils import PERMISSIONS, serialize_downtimes
from cmk.gui.openapi.api_endpoints.downtime.models.response_models import DowntimeCollectionModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.common_fields import (
    AnnotatedHostName,
    query_expression_validator,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.downtimes import Downtimes

from ._family import DOWNTIME_FAMILY


def show_downtimes_v1(
    api_context: ApiContext,
    service_description: Annotated[
        str | None,
        QueryParam(
            description=(
                "The service name. Matches service descriptions that contain the given value. "
                "No exception is raised when the specified service description does not exist. "
                "This parameter can be combined with the host_name parameter to filter for "
                "service downtimes of a specific host."
            ),
            example="Memory",
        ),
    ] = None,
    host_name: Annotated[
        AnnotatedHostName | None,
        QueryParam(
            description=(
                "The host name. No exception is raised when the specified host name does not "
                "exist. Unless otherwise restricted, the results will contain both host and "
                "service downtimes for the given host."
            ),
            example="example.com",
        ),
    ] = None,
    downtime_type: Annotated[
        Literal["host", "service", "both"],
        QueryParam(
            description="The type of the downtimes to be listed.",
            example="host",
        ),
    ] = "both",
    query: Annotated[
        Annotated[QueryExpression, query_expression_validator(Downtimes, allow_empty=True)] | None,
        QueryParam(
            description="A Livestatus filter expression for downtimes.",
            example='{"op": "and", "expr": [{"op": "=", "left": "host_name", "right": "example.com"}, {"op": "=", "left": "type", "right": "0"}]}',
        ),
    ] = None,
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)] | None,
        QueryParam(
            description="An existing site id",
            example="mysite",
        ),
    ] = None,
) -> DowntimeCollectionModel:
    """Show all scheduled downtimes"""
    q = Query(
        [
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
        ]
    )

    if downtime_type != "both":
        q = q.filter(Downtimes.is_service.equals(1 if downtime_type == "service" else 0))

    if query is not None:
        q = q.filter(query)

    if host_name is not None:
        q = q.filter(Downtimes.host_name.op("=", str(host_name)))

    if service_description is not None:
        q = q.filter(Downtimes.service_description.contains(service_description))

    return serialize_downtimes(
        q.fetchall(sites.live(), True, [site_id] if site_id is not None else None),
        host_url=api_context.host_url,
    )


ENDPOINT_SHOW_DOWNTIMES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("downtime"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=show_downtimes_v1)},
)
