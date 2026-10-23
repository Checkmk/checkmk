#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The handshake that turns the Checkmk session into a Maps daemon credential.

The SPA is already authenticated by the surrounding GUI session (2FA included);
this mints the short-lived signed ticket the daemon accepts, together with the
capabilities resolved from the caller's permissions. It is the SPA's first call
on boot and the one it re-mints from on the periodic refresh and when the open
map changes.
"""

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.maps.gui._tickets import (
    COMMAND_ACTION_PERMISSIONS,
    gather_capabilities,
    mint_stream_ticket,
    mint_ticket,
)
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import (
    MapsChoice,
    MapsTicketCapabilities,
    MapsTicketResponse,
)
from cmk.maps.rest_api.utils import MAP_VISIBILITY_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.maps.shared.ticket import MapClaim
from cmk.web.utils import permission_verification as permissions

# ``gather_capabilities`` asks for every one of these to bake the ticket, and the
# answer only shapes it, so none is required. Binding the ticket to a map
# resolves that map's visibility.
_TICKET_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("maps.use"),
        *(
            permissions.Optional(permissions.Perm(permission))
            for permission in (
                "general.edit_map",
                "maps.configure",
                "general.see_all",
                "wato.see_all_folders",
                "general.publish_map",
                "general.publish_to_groups_map",
                "general.publish_to_foreign_groups_map",
                "general.publish_to_sites_map",
                "general.act",
                *sorted(set(COMMAND_ACTION_PERMISSIONS.values())),
            )
        ),
        *MAP_VISIBILITY_PERMISSIONS,
    ]
)


def show_ticket_v1(
    name: Annotated[
        str | ApiOmitted,
        QueryParam(
            description=(
                "The map that is being opened. Binds the ticket to that map's real "
                "owner, so the daemon keys its shared broadcast loop by the map "
                "rather than by each viewer. An unknown or forbidden name yields an "
                "unbound ticket."
            ),
            example="datacenter-muc",
        ),
    ] = ApiOmitted(),
) -> MapsTicketResponse:
    """Mint a daemon ticket for the current session"""
    user.need_permission("maps.use")
    caps = gather_capabilities(user)
    map_claim: MapClaim | None = None
    if not isinstance(name, ApiOmitted) and (page := get_permitted_map(name)) is not None:
        map_claim = MapClaim(owner=str(page.config.owner), name=name)
    return MapsTicketResponse(
        ticket=mint_ticket(user, caps=caps, map_claim=map_claim),
        # The stream token travels in the URL, where it can reach an access log,
        # so it is minted separately with a reduced cap set and its own audience.
        # It exists only once a map is open -- the map list runs no stream.
        stream_token=(
            ApiOmitted() if map_claim is None else mint_stream_ticket(user, map_claim=map_claim)
        ),
        user_id=str(user.ident),
        language=user.language,
        capabilities=MapsTicketCapabilities(
            may_edit=caps["may_edit"],
            configure=caps["configure"],
            see_all=caps["see_all"],
            folder_see_all=caps["folder_see_all"],
            contact_groups=list(caps["contact_groups"]),
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


ENDPOINT_SHOW_TICKET = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_ticket"),
        link_relation="cmk/show_maps_ticket",
        method="get",
    ),
    permissions=EndpointPermissions(required=_TICKET_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_ticket_v1)},
)
