#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The SPA's first call: who is logged in and what they may do in Maps.

The daemon needs nothing from here. It authenticates the same session cookie
itself, through ``gui_session/identify``.
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
from cmk.maps.gui._capabilities import COMMAND_ACTION_PERMISSIONS, gather_capabilities
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import (
    MapsCapabilities,
    MapsChoice,
    MapsSessionResponse,
)
from cmk.maps.rest_api.utils import NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

# ``gather_capabilities`` asks for every one of these, and the answer only shapes
# what the SPA offers, so none is required.
_SESSION_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("maps.use"),
        *(
            permissions.Optional(permissions.Perm(permission))
            for permission in (
                "general.edit_map",
                "maps.configure",
                "general.publish_map",
                "general.publish_to_groups_map",
                "general.publish_to_foreign_groups_map",
                "general.publish_to_sites_map",
                "general.act",
                *sorted(set(COMMAND_ACTION_PERMISSIONS.values())),
            )
        ),
    ]
)


def show_session_v1() -> MapsSessionResponse:
    """Show the Maps capabilities of the current session"""
    user.need_permission("maps.use")
    caps = gather_capabilities(user)
    return MapsSessionResponse(
        user_id=str(user.ident),
        language=user.language,
        capabilities=MapsCapabilities(
            may_edit=caps["may_edit"],
            configure=caps["configure"],
            publish_all=caps["publish_all"],
            publish_to_groups=caps["publish_to_groups"],
            publish_to_foreign_groups=caps["publish_to_foreign_groups"],
            publish_to_sites=caps["publish_to_sites"],
            all_contact_groups=[
                MapsChoice(id=choice["id"], alias=choice["alias"])
                for choice in caps["all_contact_groups"]
            ],
            all_sites=[
                MapsChoice(id=choice["id"], alias=choice["alias"]) for choice in caps["all_sites"]
            ],
            commands=list(caps["commands"]),
        ),
    )


ENDPOINT_SHOW_SESSION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_session"),
        link_relation="cmk/show_maps_session",
        method="get",
    ),
    permissions=EndpointPermissions(required=_SESSION_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_session_v1)},
)
