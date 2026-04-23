#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
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
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href

from ._utils import (
    build_avoptions,
    build_only_sites,
    PERMISSIONS,
)
from .endpoint_family import HOST_AVAILABILITY_FAMILY
from .models.response_models import HostAvailabilityCollection, HostAvailabilityObject


def list_host_availability_v1(
    api_context: ApiContext,
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
            description="Restrict results to a specific site. If omitted, all sites are queried.",
            example="mysite",
        ),
    ] = None,
) -> HostAvailabilityCollection:
    """List availability data for all hosts"""
    user.need_permission("general.see_availability")
    avoptions = build_avoptions(time_range_from, time_range_until)
    only_sites = build_only_sites(site_id)

    raw_data, _ = get_availability_rawdata(
        what="host",
        context={},
        filterheaders="",
        only_sites=only_sites,
        av_object=None,
        include_output=False,
        include_long_output=False,
        avoptions=avoptions,
    )
    av_data = compute_availability("host", raw_data, avoptions)

    return HostAvailabilityCollection(
        id="host_availability",
        domainType="host_availability",
        value=[HostAvailabilityObject.from_internal(entry) for entry in av_data],
        links=[LinkModel.create("self", collection_href("host_availability"))],
    )


ENDPOINT_LIST_HOST_AVAILABILITY = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("host_availability"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_AVAILABILITY_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_host_availability_v1)},
)
