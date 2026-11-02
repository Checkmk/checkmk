#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The map as the SPA opens it.

The public show endpoint carries the config twice, parsed for API users and as
the signed bytes for the daemon. The SPA renders from the signed bytes, so it
fetches only those.
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
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.maps.gui._capabilities import sign_map_config
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import MapsSignedMapResponse
from cmk.maps.rest_api.utils import (
    map_from_spec,
    NO_CONFIG_CHANGE,
    PERMISSIONS,
    permitted_map_or_404,
    representable_map,
    resolve_map_link_titles,
    resolved_spec,
    visibility_from_public,
)


def _serialize_signed_map(
    page: MapPage, *, can_edit: bool, can_delete: bool
) -> MapsSignedMapResponse:
    """The map as the SPA opens it: the signed bytes it renders from and relays to
    the daemon, without the parsed copy ``serialize_map`` adds for API users.

    Raises ``ValidationError`` like ``serialize_map`` for a stored spec the
    map model no longer accepts.
    """
    cfg = page.config
    spec = resolved_spec(page)
    # Parsed only to refuse a stored spec the SPA could not render.
    map_from_spec(spec)
    signed = sign_map_config(spec, owner=str(cfg.owner))
    return MapsSignedMapResponse(
        owner=str(cfg.owner),
        visibility=visibility_from_public(cfg.public, cfg.hidden),
        is_builtin=page.is_builtin(),
        can_edit=can_edit,
        can_delete=can_delete,
        config_b64=signed["config_b64"],
        sig=signed["sig"],
        map_link_titles=resolve_map_link_titles(spec, get_permitted_map),
    )


def show_signed_map_v1(
    name: Annotated[
        str,
        PathParam(description="The unique name of the map.", example="datacenter-muc"),
    ],
) -> MapsSignedMapResponse:
    """Show a map's signed config"""
    user.need_permission("maps.use")
    page = permitted_map_or_404(name)
    with representable_map(name):
        return _serialize_signed_map(page, can_edit=page.may_edit(), can_delete=page.may_delete())


ENDPOINT_SHOW_SIGNED_MAP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("maps_signed_map", "{name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_signed_map_v1)},
)
