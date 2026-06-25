#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map endpoints for the SSE state relay.

Map *config* is owned by the GUI visuals store now (saved through the GUI's
ajax endpoints into ``var/check_mk/web/<user>/user_maps.mk``). The daemon no
longer does map CRUD; it only needs the parts that the GUI cannot do itself:

* ``register`` — cache a GUI-owned map in memory so its live state can be streamed,
* ``auto-objects`` — inflate a worldmap automap source against Livestatus.

Map background images and the image library are GUI-owned now (uploaded via
``cmk.maps.gui._images``, served statically by Apache), and stateless NagVis
``.cfg`` parsing lives in ``cmk.maps.gui._cfg_import`` — the daemon no longer
handles files or the legacy format.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from cmk.maps.backend.api.v1.connections import auth_user_scope
from cmk.maps.backend.api.v1.deps import can_create_map, get_current_user, resolve_auth_user
from cmk.maps.backend.api.v1.types import MapName
from cmk.maps.backend.core.auth import InvalidTicket, Principal, verify_map_config
from cmk.maps.backend.schemas.map import (
    MapConfig,
    MapElement,
)
from cmk.maps.backend.services import map_service, state_service

router = APIRouter()


class RegisterRequest(BaseModel):
    """Map-registration payload.

    Normal path — a GUI-signed map (``config_b64`` + ``sig``): the GUI resolved
    the config from the pagetype store and signed the exact bytes, which the
    daemon verifies here (:func:`verify_map_config`). This is what lets viewers
    of the SAME published map share one broadcast loop keyed by the map's real
    owner without a viewer being able to substitute a tampered config.

    Editor path — an unsigned ``config``: live preview of a user's OWN map with
    unsaved edits (the GUI can't sign what isn't stored yet). Only accepted when
    the ticket is unbound or scoped to the caller's own map, and always keyed
    under the caller, so it can never poison a foreign map's shared loop.
    """

    config_b64: str | None = None
    sig: str | None = None
    config: MapConfig | None = None


@router.post("/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_map(
    body: RegisterRequest, current_user: Principal = Depends(get_current_user)
) -> None:
    """Cache the map the caller opened so its live state can be streamed.

    The config is keyed by the map's real owner (``map_key_owner`` — from the
    signed ticket, never a client value), so every viewer of a published map
    shares one Livestatus poll. States stay bounded by each caller's own
    contact-group scope, so registering only controls *which* objects are
    queried, not what they may see.
    """
    if body.config_b64 is not None and body.sig is not None:
        try:
            raw = verify_map_config(body.config_b64, body.sig, owner=current_user.map_key_owner)
        except InvalidTicket as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid map signature"
            ) from exc
        # A stored map can carry a value the GUI persisted but the schema rejects
        # (e.g. an object_filter without a ``Filter:`` header). Surface that as a 422
        # rather than letting the ValidationError reach the generic 500 crash handler.
        try:
            cfg = MapConfig.model_validate(raw)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid map config"
            ) from exc
        # A map-scoped ticket must match the config it carries, so a signed blob
        # for one map can't be relayed under another map's key.
        if current_user.map_name is not None and cfg.name != current_user.map_name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Map name mismatch")
        map_service.register_map(current_user.map_key_owner, cfg)
        return
    if body.config is not None:
        # Without the edit grant a read-only user could have the daemon poll an
        # arbitrary config — AuthUser still scopes the data, but it is an unowned
        # load generator on a single-worker daemon.
        if not can_create_map(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editing maps is not allowed",
            )
        # Unsigned config is an own-map editor preview only — reject it for a
        # ticket scoped to someone else's map.
        if current_user.map_owner not in (None, current_user.name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unsigned config not allowed for a foreign map",
            )
        # A map-scoped ticket must match the config it carries — mirror the
        # signed path's name check so a ticket for one of the caller's maps can't
        # register a preview under a different name in their namespace.
        if current_user.map_name is not None and body.config.name != current_user.map_name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Map name mismatch")
        map_service.register_map(current_user.map_key_owner, body.config)
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing map config"
    )


@router.get("/{name}/auto-objects", response_model=list[MapElement])
async def get_auto_objects(
    name: MapName, current_user: Principal = Depends(get_current_user)
) -> list[MapElement]:
    """Return objects synthesised from a worldmap automap source.

    Empty for maps without ``auto_source`` configured. The objects are
    transient — they're never persisted, so the editor only ever sees the
    operator's curated set.
    """
    cfg = map_service.get_map(current_user.map_key_owner, name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return []
    # Scope the geo-host query to the caller's contact groups, like every other
    # read path (a non-see-all user must not enumerate hosts outside their
    # groups). Without the AuthUser context the underlying Livestatus query runs
    # unscoped and returns every geo-tagged host in the site.
    auth_user = resolve_auth_user(current_user)
    async with auth_user_scope(connection, auth_user):
        inflated = await state_service.inflate_auto_objects(cfg, connection)
    persisted_ids = {o.id for o in cfg.objects}
    return [o for o in inflated if o.id not in persisted_ids]
