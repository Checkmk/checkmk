#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Read-only views on the GUI-owned Maps image library.

Uploads and deletes stay AjaxPages in :mod:`cmk.maps.gui._images`: the versioned
REST framework has no multipart support, and the delete path is a write with a
confirm round-trip.
"""

from typing import Annotated

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
from cmk.gui.openapi.restful_objects.constructors import collection_href, object_action_href
from cmk.maps.gui._images import find_image_usage, image_list, require_valid_image_name
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import (
    MapsImage,
    MapsImagesResponse,
    MapsImageUsage,
    MapsImageUsageResponse,
)
from cmk.maps.rest_api.utils import CONFIGURE_PERMISSIONS, PERMISSIONS

_READ_ONLY = EndpointBehavior(skip_locking=True, update_config_generation=False)


def list_images_v1() -> MapsImagesResponse:
    """Show the image library"""
    user.need_permission("maps.use")
    return MapsImagesResponse(
        images=[
            MapsImage(name=entry.name, url=entry.url, builtin=entry.builtin)
            for entry in image_list()
        ]
    )


def show_image_usage_v1(
    name: Annotated[
        str,
        PathParam(description="The image's file name.", example="server.svg"),
    ],
) -> MapsImageUsageResponse:
    """Show which maps use an image"""
    user.need_permission("maps.configure")
    require_valid_image_name(name)
    return MapsImageUsageResponse(
        usage=[
            MapsImageUsage(
                map_name=entry.map_name,
                alias=entry.alias,
                object_ids=entry.object_ids,
                is_background=entry.is_background,
            )
            for entry in find_image_usage(name)
        ]
    )


ENDPOINT_LIST_IMAGES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_image"),
        link_relation="cmk/list_maps_images",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=_READ_ONLY,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_images_v1)},
)

ENDPOINT_SHOW_IMAGE_USAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("maps_image", "{name}", "usage"),
        link_relation="cmk/show_maps_image_usage",
        method="get",
    ),
    permissions=EndpointPermissions(required=CONFIGURE_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=_READ_ONLY,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_image_usage_v1)},
)
