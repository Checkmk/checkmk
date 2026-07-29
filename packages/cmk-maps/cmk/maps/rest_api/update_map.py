#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.exceptions import MKGeneralException
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
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException, RestAPIRequestGeneralException
from cmk.maps.gui._pages import _authorized_public
from cmk.maps.gui.store import get_own_map, get_permitted_map, save_map
from cmk.maps.rest_api.endpoint_family import MAPS_FAMILY
from cmk.maps.rest_api.models.request_models import MapRequest
from cmk.maps.rest_api.models.response_models import MapObject
from cmk.maps.rest_api.utils import (
    map_etag,
    public_request_from_visibility,
    RW_PERMISSIONS,
    serialize_map,
    spec_from_map,
    validate_visibility,
)


def update_map_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        PathParam(description="The unique name of the map.", example="datacenter-muc"),
    ],
    body: MapRequest,
) -> ApiResponse[MapObject]:
    """Update a map"""
    user.need_permission("maps.use")
    # The map to write is identified by the path; a body naming a different map
    # would otherwise be stored under the path key with a mismatched ``name`` in
    # its payload (and get GUI-signed under that mismatched name).
    if body.config.name != name:
        raise RestAPIRequestGeneralException(
            status=400,
            title="Map name mismatch",
            detail=f"The body's config.name {body.config.name!r} must match the path name {name!r}.",
        )
    # ``user.ident`` narrows to a guaranteed UserId and raises (not stripped
    # under ``python -O``) if the request is somehow unauthenticated.
    user_id = user.ident
    # Resolve the instance the user sees (an own map shadows a built-in / foreign
    # one of the same name), then apply the pagetype permission model: a foreign
    # map is edited in place (needs "edit foreign maps"); an own map or a built-in
    # is written under the session user, so customizing a built-in transparently
    # creates an own override.
    page = get_permitted_map(name)
    if page is None:
        raise RestAPIRequestGeneralException(
            status=404,
            title=f"The map {name!r} does not exist.",
            detail="No map with this name is visible to you.",
        )
    owner = page.config.owner
    if owner and str(owner) != str(user_id):
        if not page.may_edit():
            raise RestAPIRequestGeneralException(
                status=403,
                title=f"You are not allowed to edit the map {name!r}.",
                detail="Editing a foreign map requires the 'edit foreign maps' permission.",
            )
        target_owner = owner
    else:
        if not user.may("general.edit_map"):
            raise RestAPIRequestGeneralException(
                status=403,
                title=f"You are not allowed to edit the map {name!r}.",
                detail="Creating or customizing maps requires the edit permission.",
            )
        target_owner = user_id
    if api_context.etag.enabled:
        api_context.etag.verify(map_etag(page))

    # Preserve the stored visibility of the written instance when the request
    # omits it (routine autosaves), so an edit never silently resets sharing;
    # a brand-new own override defaults to private.
    existing_own = get_own_map(target_owner, name)
    if not isinstance(body.visibility, ApiOmitted):
        validate_visibility(body.visibility)
        public = _authorized_public(public_request_from_visibility(body.visibility))
    elif existing_own is not None and existing_own.config.public is not None:
        public = existing_own.config.public
    else:
        public = False
    try:
        save_map(target_owner, name, spec_from_map(body.config), public)
    except MKGeneralException as exc:
        # A failed store write (disk full, unwritable profile) would otherwise
        # surface as an uncaught 500 with a crash report; answer a clean error.
        raise ProblemException(
            status=500,
            title="The map could not be stored.",
            detail=str(exc),
        ) from exc
    updated = get_own_map(target_owner, name)
    assert updated is not None
    return ApiResponse(
        status_code=200,
        body=serialize_map(updated, can_edit=updated.may_edit(), can_delete=updated.may_delete()),
        etag=map_etag(updated),
    )


ENDPOINT_UPDATE_MAP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("map", "{name}"),
        link_relation=".../update",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=update_map_v1)},
)
