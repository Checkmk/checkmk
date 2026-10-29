#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Which map a user sees under a name, for the Maps daemon.

The daemon keys one broadcast loop per map by its owner, so that every viewer of
a published map shares one Livestatus poll. Only the GUI knows which map a name
means for a user: their own, one published to them or a built-in one.
"""

from cmk.ccc.user import UserId
from cmk.gui.oauth.openapi.utils import require_site_internal_caller
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.session_context import UserContext
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsAccessRequest
from cmk.maps.rest_api.internal.models.response_models import MapsAccessResponse
from cmk.maps.rest_api.utils import MAP_VISIBILITY_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions


def resolve_access_v1(api_context: ApiContext, body: MapsAccessRequest) -> MapsAccessResponse:
    """Resolve the map a user sees under a name

    Reserved for the Maps daemon, which calls it with the site-internal secret
    for a user it identified from their GUI session.
    """
    require_site_internal_caller(api_context)
    with UserContext(UserId(body.user_id), api_context.config.user_permissions()):
        page = get_permitted_map(body.name)
    if page is None:
        return MapsAccessResponse()
    return MapsAccessResponse(owner=str(page.config.owner))


ENDPOINT_RESOLVE_ACCESS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_access", "resolve"),
        link_relation="cmk/resolve_maps_access",
        method="post",
    ),
    permissions=EndpointPermissions(required=permissions.AllPerm(MAP_VISIBILITY_PERMISSIONS)),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=resolve_access_v1)},
)
