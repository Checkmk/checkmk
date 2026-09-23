#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.maps.gui.store import get_permitted_maps
from cmk.maps.rest_api.endpoint_family import MAPS_FAMILY
from cmk.maps.rest_api.models.response_models import MapCollection
from cmk.maps.rest_api.utils import PERMISSIONS, serialize_map_list_entry


def list_maps_v1() -> MapCollection:
    """Show all maps"""
    user.need_permission("maps.use")
    return MapCollection(
        id="map",
        domainType="map",
        value=[
            serialize_map_list_entry(page, can_edit=page.may_edit(), can_delete=page.may_delete())
            for page in get_permitted_maps()
        ],
        links=[LinkModel.create("self", collection_href("map"))],
    )


ENDPOINT_LIST_MAPS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("map"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_maps_v1)},
)
