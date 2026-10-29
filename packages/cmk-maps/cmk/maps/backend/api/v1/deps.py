#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared FastAPI dependencies — authentication by the GUI session.

Every request, the event stream included, carries the GUI session cookie the
browser sends to the site anyway. :class:`~cmk.maps.backend.core.auth.GuiAuth`
asks the GUI who is behind it and, for a request about a map, which map the name
means for that user.
"""

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from cmk.fastapi.gui_session import Rejected, SessionCookie, Unavailable
from cmk.maps.backend.api.v1.types import MapName
from cmk.maps.backend.core.auth import Forbidden, GuiAuth, NoMap, Principal
from cmk.maps.backend.core.ratelimit import rest_read_limiter
from cmk.maps.backend.schemas.map import MapConfig
from cmk.maps.backend.services import map_service

__all__ = [
    "GuiAuthDep",
    "Principal",
    "SessionCookieDep",
    "can_configure",
    "can_create_map",
    "get_current_user",
    "get_gui_auth",
    "get_map_owner",
    "get_map_viewer",
    "rate_limited_map_read",
    "rate_limited_read",
    "registered_map",
    "require_connection_read",
    "resolve_auth_user",
]

session_cookie = SessionCookie()

SessionCookieDep = Annotated[str, Depends(session_cookie)]


def get_gui_auth(request: Request) -> GuiAuth:
    """What the lifespan set up to ask the GUI about a session."""
    auth: GuiAuth = request.app.state.gui_auth
    return auth


GuiAuthDep = Annotated[GuiAuth, Depends(get_gui_auth)]


def _user_verdict(result: Principal | Rejected | Forbidden | Unavailable) -> Principal:
    match result:
        case Principal():
            return result
        case Rejected():
            raise session_cookie.make_not_authenticated_error()
        case Forbidden():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Maps access required"
            )
        case Unavailable():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not available right now",
            )


def _map_verdict(result: str | NoMap | Unavailable, name: str) -> str | None:
    match result:
        case str():
            return result
        case NoMap():
            return None
        case Unavailable():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot resolve map '{name}' right now",
            )


async def get_current_user(cookie: SessionCookieDep, auth: GuiAuthDep) -> Principal:
    """The user behind the request's GUI session, or the refusal of the request."""
    return _user_verdict(await auth.principal(cookie, now=time.monotonic()))


async def get_map_owner(
    name: MapName,
    auth: GuiAuthDep,
    current_user: Principal = Depends(get_current_user),
) -> str | None:
    """The owner of the map the user sees under ``name``, ``None`` if they see none."""
    return _map_verdict(await auth.map_owner(current_user, name, now=time.monotonic()), name)


async def get_map_viewer(
    name: MapName,
    current_user: Principal = Depends(get_current_user),
    owner: str | None = Depends(get_map_owner),
) -> Principal:
    """The user, viewing the map they see under ``name``, or 404."""
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return current_user.viewing(owner, name)


def _rate_limited(user: Principal) -> Principal:
    """Guard the expensive Livestatus readers with a per-user budget.

    Keyed by the authenticated identity (not IP), so a valid session can't drive
    unbounded topology / metric-history / search load, and one user's flood can't
    lock out another. See ``rest_read_limiter`` for the budget.
    """
    key = user.name
    if rest_read_limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limited",
            headers={"Retry-After": str(int(rest_read_limiter.retry_after(key)) + 1)},
        )
    rest_read_limiter.record(key)
    return user


async def rate_limited_read(current_user: Principal = Depends(get_current_user)) -> Principal:
    return _rate_limited(current_user)


async def rate_limited_map_read(
    # Before the viewer: resolving the map asks the GUI, which the budget is there to spare.
    _budget: Principal = Depends(rate_limited_read),
    viewer: Principal = Depends(get_map_viewer),
) -> Principal:
    return viewer


# ---------------------------------------------------------------------------
# Capability predicates
# ---------------------------------------------------------------------------


def can_configure(principal: Principal) -> bool:
    """Read the full connection details (Checkmk's ``maps.configure``)."""
    return principal.configure


def can_create_map(principal: Principal) -> bool:
    """Register unsigned editor previews and read the connection list — Checkmk's
    ``general.edit_map`` (per-map edit rights are enforced by the GUI on save)."""
    return principal.may_edit


def resolve_auth_user(principal: Principal) -> str | None:
    """Livestatus ``AuthUser`` to scope queries, or ``None`` for see-all users."""
    return principal.auth_user


# ---------------------------------------------------------------------------
# FastAPI guard dependencies
# ---------------------------------------------------------------------------


async def require_connection_read(current_user: Principal = Depends(get_current_user)) -> Principal:
    """Read-only access to the connection list.

    Map creators need it to pick a connection, so this admits ``can_create_map``
    in addition to ``can_configure``. Connections themselves are WATO/admin-owned
    and read-only in the daemon, so there is no daemon-side mutation guard.
    """
    if not (can_configure(current_user) or can_create_map(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Maps configuration access required"
        )
    return current_user


def registered_map(user: Principal, name: str) -> MapConfig:
    """Resolve the viewed map's config under its real owner, or 404.

    Keyed by ``map_key_owner`` (the map's owner, as the GUI named it), so all
    viewers of a published map resolve the one config registered under it."""
    cfg = map_service.get_map(user.map_key_owner, name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg
