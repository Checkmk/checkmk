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

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ValidationError

from cmk.maps.backend.api.v1.connections import auth_user_scope
from cmk.maps.backend.api.v1.deps import (
    can_create_map,
    charge,
    get_current_user,
    get_map_owner,
    GuiAuthDep,
    rate_limited_map_read,
    registered_map,
    resolve_auth_user,
    within_read_budget,
)
from cmk.maps.backend.api.v1.states import (
    map_states_response,
    tell_map_saved,
    view_preview,
    ViewPreview,
)
from cmk.maps.backend.api.v1.types import MapName
from cmk.maps.backend.core.auth import InvalidSignature, Principal, verify_map_config
from cmk.maps.backend.core.ratelimit import rest_read_limiter
from cmk.maps.backend.schemas.map import (
    MapConfig,
    MapElement,
)
from cmk.maps.backend.schemas.state import MapStates
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
    the name means the caller's own map for them, and always keyed under the
    caller, so it can never poison a foreign map's shared loop.
    """

    config_b64: str | None = None
    sig: str | None = None
    config: MapConfig | None = None
    # The signed config was just saved, so the open views of the map compare versions.
    saved: bool = False


class SavedRequest(BaseModel):
    """A GUI-signed map that was just saved."""

    config_b64: str
    sig: str


def _register_signed(
    name: str, config_b64: str, sig: str, owner: str | None, current_user: Principal, *, saved: bool
) -> tuple[str, MapConfig]:
    """The owner the map is registered under, and its config."""
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    try:
        raw = verify_map_config(config_b64, sig, owner=owner)
    except InvalidSignature as exc:
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
    # The owner was resolved for ``name``, so the signed config must be that map's.
    if cfg.name != name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Map name mismatch")
    if not map_service.register_signed_map(owner, cfg):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The map was saved since")
    if saved and current_user.may_save(owner):
        tell_map_saved(owner, name, sig)
    return owner, cfg


@router.post("/{name}/register", response_model=MapStates)
async def register_map(
    name: MapName,
    body: RegisterRequest,
    auth: GuiAuthDep,
    # Counted, never refused here: a spent budget still registers the map and
    # refuses only its states.
    within_budget: bool = Depends(within_read_budget),
    current_user: Principal = Depends(get_current_user),
    owner: str | None = Depends(get_map_owner),
    preview: ViewPreview = Depends(view_preview),
) -> Response:
    """Cache the map the caller opened so its live state can be streamed, and
    answer with its full states, so opening a map takes one round trip. A
    settings preview's unsaved view applies to the answer, not to the cache.
    The call counts against the read budget; once it is spent, the map is
    registered all the same, so its stream still runs, but its states are refused.

    The config is keyed by the map's real owner, as the GUI names it for the
    caller, never a client value. So every viewer of a published map shares one
    Livestatus poll. States stay bounded by each caller's own contact-group
    scope, so registering only controls *which* objects are queried, not what
    they may see.
    """
    if body.config_b64 is not None and body.sig is not None:
        owner, cfg = _register_signed(
            name,
            body.config_b64,
            body.sig,
            owner,
            current_user,
            saved=body.saved and within_budget,
        )
        if not within_budget:
            charge(rest_read_limiter, current_user.name)
        return await map_states_response(
            preview.apply(cfg), current_user.viewing(owner, name), auth
        )
    if body.config is not None:
        # Without the edit grant a read-only user could have the daemon poll an
        # arbitrary config — AuthUser still scopes the data, but it is an unowned
        # load generator on a single-worker daemon.
        if not can_create_map(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editing maps is not allowed",
            )
        # Every read of the map needs a map the GUI names, so a preview without one
        # could never be streamed.
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
            )
        # Unsigned config is an own-map editor preview only — reject it for a
        # name that means someone else's map for the caller.
        if owner != current_user.name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unsigned config not allowed for a foreign map",
            )
        if body.config.name != name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Map name mismatch")
        map_service.register_map(current_user.name, body.config)
        if not within_budget:
            charge(rest_read_limiter, current_user.name)
        return await map_states_response(
            preview.apply(body.config), current_user.viewing(current_user.name, name), auth
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing map config"
    )


@router.post("/{name}/saved", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def register_saved_map(
    name: MapName,
    body: SavedRequest,
    # Counted, never refused here: a spent budget still registers the map, but
    # its open views are not told.
    within_budget: bool = Depends(within_read_budget),
    current_user: Principal = Depends(get_current_user),
    owner: str | None = Depends(get_map_owner),
) -> Response:
    """Cache the map just saved and tell its open views which version is saved,
    like ``register`` but without its states, for a view that shows them already."""
    _register_signed(name, body.config_b64, body.sig, owner, current_user, saved=within_budget)
    # Only the states would ask Livestatus.
    if within_budget:
        rest_read_limiter.refund(current_user.name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{name}/auto-objects", response_model=list[MapElement])
async def get_auto_objects(
    name: MapName, current_user: Principal = Depends(rate_limited_map_read)
) -> list[MapElement]:
    """Return objects synthesised from a worldmap automap source.

    Empty for maps without ``auto_source`` configured. The objects are
    transient — they're never persisted, so the editor only ever sees the
    operator's curated set.
    """
    cfg = registered_map(current_user, name)
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
