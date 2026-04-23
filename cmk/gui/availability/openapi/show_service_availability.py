#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from http import HTTPStatus
from typing import Annotated

from pydantic import AwareDatetime

from cmk.ccc.site import SiteId
from cmk.gui.availability.computation import compute_availability
from cmk.gui.availability.rawdata import get_availability_rawdata
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.restful_objects.constructors import sub_object_href
from cmk.gui.openapi.utils import ProblemException

from ._utils import (
    build_avoptions,
    build_only_sites,
    build_service_filterheader,
    PERMISSIONS,
)
from .endpoint_family import SERVICE_AVAILABILITY_FAMILY
from .models.response_models import ServiceAvailabilityObject


def show_service_availability_v1(
    api_context: ApiContext,
    host_name: Annotated[
        AnnotatedHostName,
        PathParam(
            description="The host name the service runs on.",
            example="my-host",
        ),
    ],
    service_name: Annotated[
        str,
        PathParam(
            description="The service name.",
            example="CPU load",
        ),
    ],
    time_range_from: Annotated[
        dt.datetime,
        AwareDatetime,
        QueryParam(
            description="Start of the time range as an ISO 8601 datetime with timezone.",
            example="2023-11-14T22:13:20+00:00",
        ),
    ],
    time_range_until: Annotated[
        dt.datetime,
        AwareDatetime,
        QueryParam(
            description="End of the time range as an ISO 8601 datetime with timezone.",
            example="2023-11-15T22:13:20+00:00",
        ),
    ],
    site_id: Annotated[
        SiteId | None,
        QueryParam(
            description="Restrict the query to a specific site. Required when the same host name exists on multiple sites.",
            example="mysite",
        ),
    ] = None,
) -> ServiceAvailabilityObject:
    """Show availability data for a single service"""
    user.need_permission("general.see_availability")
    avoptions = build_avoptions(time_range_from, time_range_until)
    only_sites = build_only_sites(site_id)

    raw_data, _ = get_availability_rawdata(
        what="service",
        context={},
        filterheaders=build_service_filterheader(host_name, service_name),
        only_sites=only_sites,
        av_object=None,
        include_output=False,
        include_long_output=False,
        avoptions=avoptions,
    )
    av_data = compute_availability("service", raw_data, avoptions)

    if not av_data:
        raise ProblemException(
            title="Object does not exist",
            detail=f"No availability data found for service '{service_name}' on host '{host_name}'.",
            status=HTTPStatus.NOT_FOUND,
        )

    return ServiceAvailabilityObject.from_internal(av_data[0])


ENDPOINT_SHOW_SERVICE_AVAILABILITY = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("service_availability", "{service_name}", "host", "{host_name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_AVAILABILITY_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_service_availability_v1)},
)
