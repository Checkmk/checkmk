#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A map's background image.

Only the file is stored here; the map's ``background_image`` field is written by
the map save, so the caller adopts the filename this answers. The work, and the
reasoning behind the capability-carrying filename and the permission split
against the shared image library, lives in :mod:`cmk.maps.gui._images`; the file
rides base64-encoded in the body (see ``_base64_decoder``).
"""

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.maps.gui._images import delete_background, upload_background
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsBackgroundUploadRequest
from cmk.maps.rest_api.internal.models.response_models import MapsBackgroundResponse
from cmk.maps.rest_api.utils import (
    MAP_EDIT_PERMISSIONS,
    MAP_VISIBILITY_PERMISSIONS,
    NO_CONFIG_CHANGE,
)
from cmk.web.utils import permission_verification as permissions

_MapName = Annotated[
    str,
    PathParam(description="The map the background belongs to.", example="datacenter-muc"),
]


def upload_background_v1(
    name: _MapName, body: MapsBackgroundUploadRequest
) -> MapsBackgroundResponse:
    """Store a map's background image"""
    user.need_permission("maps.use")
    return MapsBackgroundResponse(
        filename=upload_background(name, body.filename, body.content_type, body.content)
    )


def delete_background_v1(name: _MapName) -> None:
    """Remove a map's background image"""
    user.need_permission("maps.use")
    delete_background(name)


# Sub-resources of a map rather than their own domain type: a background exists
# only for one map and is authorized by that map's edit right.
_BACKGROUND_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), *MAP_VISIBILITY_PERMISSIONS, *MAP_EDIT_PERMISSIONS]
)

ENDPOINT_UPLOAD_BACKGROUND = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("map", "{name}", "upload-background"),
        link_relation="cmk/upload_maps_background",
        method="post",
    ),
    permissions=EndpointPermissions(required=_BACKGROUND_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=upload_background_v1)},
)

ENDPOINT_DELETE_BACKGROUND = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("map", "{name}", "delete-background"),
        link_relation="cmk/delete_maps_background",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=_BACKGROUND_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=delete_background_v1)},
)
