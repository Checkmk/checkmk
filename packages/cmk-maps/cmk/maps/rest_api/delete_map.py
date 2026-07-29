#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.maps.gui.store import delete_map, get_permitted_map
from cmk.maps.rest_api.endpoint_family import MAPS_FAMILY
from cmk.maps.rest_api.utils import map_etag, RW_PERMISSIONS


def delete_map_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        PathParam(description="The unique name of the map.", example="datacenter-muc"),
    ],
) -> None:
    """Delete a map"""
    user.need_permission("maps.use")
    # Resolve the instance the user sees and gate on the pagetype delete
    # permission (``MapPage.may_delete``): built-ins are never deletable, own maps
    # need the edit permission, foreign maps need "delete foreign maps". The map
    # is removed from its actual owner's store, so an admin can delete a foreign
    # map without forking it first.
    page = get_permitted_map(name)
    if page is None:
        raise RestAPIRequestGeneralException(
            status=404,
            title=f"The map {name!r} does not exist.",
            detail="No map with this name is visible to you.",
        )
    if not page.may_delete():
        raise RestAPIRequestGeneralException(
            status=403,
            title=f"You are not allowed to delete the map {name!r}.",
            detail="Deleting this map requires ownership or the 'delete foreign maps' permission.",
        )
    if api_context.etag.enabled:
        api_context.etag.verify(map_etag(page))
    delete_map(page.config.owner, name)


ENDPOINT_DELETE_MAP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("map", "{name}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    behavior=EndpointBehavior(etag="input"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=delete_map_v1)},
)
