#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The GUI-owned Maps image library.

The files live under ``var/maps/images`` and are served statically by Apache;
what this exposes is the library's listing, its usage scan and its two writes.
The work itself lives in :mod:`cmk.maps.gui._images`; an upload carries its file
base64-encoded in the body (see ``_base64_decoder``).
"""

from typing import Annotated

from pydantic import TypeAdapter

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import (
    collection_href,
    object_action_href,
    object_href,
)
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.maps.gui._images import (
    delete_image,
    find_image_usage,
    image_list,
    ImageUsageEntry,
    require_valid_image_name,
    upload_image,
)
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsImageUploadRequest
from cmk.maps.rest_api.internal.models.response_models import (
    MapsImage,
    MapsImagesResponse,
    MapsImageUsage,
    MapsImageUsageResponse,
)
from cmk.maps.rest_api.utils import MAP_VISIBILITY_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

_UPLOAD_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), permissions.Perm("maps.configure")]
)
# Showing an image's use, and deleting it, scans the maps the user may see.
_USAGE_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), permissions.Perm("maps.configure"), *MAP_VISIBILITY_PERMISSIONS]
)


def list_images_v1() -> MapsImagesResponse:
    """Show the image library"""
    user.need_permission("maps.use")
    return MapsImagesResponse(
        images=[
            MapsImage(name=entry.name, url=entry.url, builtin=entry.builtin)
            for entry in image_list()
        ]
    )


# The 409's usage list, in the shape the usage endpoint answers with.
_USAGE_ADAPTER: TypeAdapter[list[MapsImageUsage]] = TypeAdapter(list[MapsImageUsage])


def _usage(entry: ImageUsageEntry) -> MapsImageUsage:
    return MapsImageUsage(
        map_name=entry.map_name,
        alias=entry.alias,
        object_ids=entry.object_ids,
        is_background=entry.is_background,
    )


def show_image_usage_v1(
    name: Annotated[
        str,
        PathParam(description="The image's file name.", example="server.svg"),
    ],
) -> MapsImageUsageResponse:
    """Show which maps use an image"""
    user.need_permission("maps.use")
    user.need_permission("maps.configure")
    require_valid_image_name(name)
    return MapsImageUsageResponse(usage=[_usage(entry) for entry in find_image_usage(name)])


def upload_image_v1(body: MapsImageUploadRequest) -> MapsImage:
    """Add an image to the library"""
    user.need_permission("maps.use")
    user.need_permission("maps.configure")
    entry = upload_image(body.filename, body.content_type, body.content)
    return MapsImage(name=entry.name, url=entry.url, builtin=entry.builtin)


def delete_image_v1(
    name: Annotated[
        str,
        PathParam(description="The image's file name.", example="server.svg"),
    ],
    force: Annotated[
        bool,
        QueryParam(
            description=(
                "Delete the image even though maps still reference it. Without it "
                "an image in use is kept and the request is refused with the maps "
                "that use it, so the operator can be shown what would break."
            ),
            example="False",
        ),
    ] = False,
) -> None:
    """Delete an image from the library"""
    user.need_permission("maps.use")
    user.need_permission("maps.configure")
    if blocking := delete_image(name, force):
        usage = [_usage(entry) for entry in blocking]
        raise ProblemException(
            status=409,
            title=f"The image {name!r} is still in use.",
            detail="Repeat with 'force' to delete it and leave those maps without it.",
            ext=EXT({"usage": _USAGE_ADAPTER.dump_python(usage, mode="json", by_alias=True)}),
        )


ENDPOINT_LIST_IMAGES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_image"),
        link_relation="cmk/list_maps_images",
        method="get",
    ),
    permissions=EndpointPermissions(required=permissions.Perm("maps.use")),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_images_v1)},
)

ENDPOINT_SHOW_IMAGE_USAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("maps_image", "{name}", "usage"),
        link_relation="cmk/show_maps_image_usage",
        method="get",
    ),
    permissions=EndpointPermissions(required=_USAGE_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_image_usage_v1)},
)


ENDPOINT_UPLOAD_IMAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_image"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=_UPLOAD_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=upload_image_v1)},
)

# 409 with the blocking maps rather than a 200 that deleted nothing, so a client
# that only reads the status is never told an image is gone while it is not.
ENDPOINT_DELETE_IMAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("maps_image", "{name}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=_USAGE_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={
        APIVersion.INTERNAL: EndpointHandler(handler=delete_image_v1, additional_status_codes=[409])
    },
)
