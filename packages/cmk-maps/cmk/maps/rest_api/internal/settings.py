#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The GUI-owned authoring defaults, for the Maps SPA.

These are Checkmk global settings living in the Maps config domain, so the GUI
resolves them (:mod:`cmk.maps.gui._settings`) and the daemon never sees them.
The SPA fetches them here rather than receiving them as page props: a second
data-assembly path would have to be kept in step with this one, and its
optionality would reach every consumer of the values.
"""

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.maps.gui._settings import default_tile_template, map_object_defaults, tile_csp_sources
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import (
    MapsAuthoringSettings,
    MapsAuthoringSettingsResponse,
    MapsTileSource,
)
from cmk.maps.rest_api.utils import NO_CONFIG_CHANGE, PERMISSIONS


def show_authoring_settings_v1() -> MapsAuthoringSettingsResponse:
    """Show the map and object authoring defaults"""
    user.need_permission("maps.use")
    return MapsAuthoringSettingsResponse(
        settings=MapsAuthoringSettings(**map_object_defaults()),
        tiles=MapsTileSource(
            default_url=default_tile_template(),
            allowed_sources=tile_csp_sources(),
        ),
    )


ENDPOINT_SHOW_AUTHORING_SETTINGS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_settings"),
        link_relation="cmk/show_maps_authoring_settings",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_authoring_settings_v1)},
)
