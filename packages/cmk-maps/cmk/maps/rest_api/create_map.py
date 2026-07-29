#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import ProblemException, RestAPIRequestGeneralException
from cmk.maps.gui._pages import _authorized_public
from cmk.maps.gui.store import create_map, get_own_map, is_valid_map_name
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


def create_map_v1(api_context: ApiContext, body: MapRequest) -> ApiResponse[MapObject]:  # noqa: ARG001
    """Create a map"""
    user.need_permission("maps.use")
    # ``maps.use`` only grants viewing; creating a map is the pagetype create
    # grant (``general.edit_map``), gated separately — the same permission the GUI
    # "Add map" entry and the update endpoint require.
    if not user.may("general.edit_map"):
        raise RestAPIRequestGeneralException(
            status=403,
            title="You are not allowed to create maps.",
            detail="Creating maps requires the 'Customize and use maps' permission.",
        )
    # ``user.ident`` narrows to a guaranteed UserId and raises (not stripped
    # under ``python -O``) if the request is somehow unauthenticated.
    user_id = user.ident
    name = body.config.name
    if not is_valid_map_name(name):
        raise RestAPIRequestGeneralException(
            status=400,
            title="Invalid map name",
            detail="A map name may only contain letters, digits, underscore and hyphen.",
        )
    if not isinstance(body.visibility, ApiOmitted):
        validate_visibility(body.visibility)
        requested = public_request_from_visibility(body.visibility)
    else:
        requested = False
    try:
        # Atomic create: the store serializes the existence check and the write under
        # a file lock, so two concurrent POSTs of the same name can't both pass and
        # have the second silently overwrite the first.
        created = create_map(
            user_id, name, spec_from_map(body.config), _authorized_public(requested)
        )
    except MKGeneralException as exc:
        # A failed store write (disk full, unwritable profile) would otherwise
        # surface as an uncaught 500 with a crash report; answer a clean error.
        raise ProblemException(
            status=500,
            title="The map could not be stored.",
            detail=str(exc),
        ) from exc
    if not created:
        # 409 Conflict: the collection POST clashes with an existing resource. A
        # distinct status (not the 400 used for an invalid name) lets clients tell
        # "name taken" from "name malformed" — the SPA surfaces each differently.
        raise RestAPIRequestGeneralException(
            status=409,
            title=f"The map {name!r} already exists.",
            detail="Use the update endpoint to modify an existing map.",
        )
    page = get_own_map(user_id, name)
    assert page is not None
    return ApiResponse(
        status_code=200,
        body=serialize_map(page, can_edit=page.may_edit(), can_delete=page.may_delete()),
        etag=map_etag(page),
    )


ENDPOINT_CREATE_MAP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("map"),
        link_relation="cmk/create",
        method="post",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=create_map_v1)},
)
