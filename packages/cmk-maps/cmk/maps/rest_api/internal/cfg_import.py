#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Import a legacy NagVis ``.cfg`` into a Maps map.

Parsing only: the answer is a draft the editor shows, which the operator then
saves through the Maps REST API like any other map. The parser lives in
:mod:`cmk.maps.gui._cfg_import`; the file rides base64-encoded in the body (see
``_base64_decoder``).
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
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.maps.gui._cfg_import import parse_cfg_upload
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsCfgImportRequest
from cmk.maps.rest_api.internal.models.response_models import MapsCfgImportResponse
from cmk.maps.rest_api.utils import NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions


def parse_cfg_v1(body: MapsCfgImportRequest) -> MapsCfgImportResponse:
    """Parse a legacy NagVis map file into a map draft"""
    user.need_permission("maps.use")
    # Importing produces a map to save, so it needs the pagetype create grant.
    user.need_permission("general.edit_map")
    map_config, warnings = parse_cfg_upload(body.filename, body.content)
    return MapsCfgImportResponse(map_config=dict(map_config), warnings=warnings)


ENDPOINT_PARSE_CFG = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("map", "parse-cfg"),
        link_relation="cmk/parse_maps_cfg",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [permissions.Perm("maps.use"), permissions.Perm("general.edit_map")]
        )
    ),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=parse_cfg_v1)},
)
