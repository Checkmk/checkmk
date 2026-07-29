#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import ValidationError

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.rest_api.endpoint_family import MAPS_FAMILY
from cmk.maps.rest_api.models.response_models import MapObject
from cmk.maps.rest_api.utils import map_etag, PERMISSIONS, serialize_map


def show_map_v1(
    name: Annotated[
        str,
        PathParam(description="The unique name of the map.", example="datacenter-muc"),
    ],
) -> ApiResponse[MapObject]:
    """Show a map"""
    user.need_permission("maps.use")
    page = get_permitted_map(name)
    if page is None:
        raise RestAPIRequestGeneralException(
            status=404,
            title=f"The map {name!r} does not exist.",
            detail="No map with this name is visible to you.",
        )
    try:
        body = serialize_map(page, can_edit=page.may_edit(), can_delete=page.may_delete())
    except ValidationError as exc:
        # A stored spec that no longer fits the model (legacy/half-written map, as
        # the list tolerates via ``utils._list_view``) is a recoverable data state,
        # so answer 409 instead of crashing with an unhandled 500.
        raise RestAPIRequestGeneralException(
            status=409,
            title=f"The map {name!r} cannot be represented.",
            detail="Its stored configuration is incompatible with the current map "
            "model and likely needs to be migrated or re-saved.",
        ) from exc
    return ApiResponse(
        status_code=200,
        body=body,
        etag=map_etag(page),
    )


ENDPOINT_SHOW_MAP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("map", "{name}"),
        link_relation="cmk/show",
        method="get",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_map_v1)},
)
