#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared FastAPI dependencies — Checkmk-native ticket authentication.

Every normal call carries the full-capability API ticket in the ``X-Maps-Ticket``
header (a dedicated header because the site Apache claims ``Authorization`` for
its own HTTP Basic auth). The SSE endpoint instead carries a reduced-capability
stream token as a ``?token=`` query parameter, because ``EventSource`` cannot set
headers. The two are bound to different audiences (see
:mod:`cmk.maps.shared.ticket`): the header path requires the API audience
and the SSE path the stream audience, so a URL stream token — which can leak into
access logs — is rejected on every REST endpoint and can neither drive the API
nor escalate privilege. Both are minted by ``cmk.maps.gui`` for the logged-in
Checkmk user and validated here against the shared site-internal secret; the
resulting :class:`Principal` carries the user's pre-resolved capabilities, so the
daemon performs no further RBAC lookups of its own.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from cmk.maps.backend.core.auth import (
    InvalidTicket,
    Principal,
    validate_stream_ticket,
    validate_ticket,
)
from cmk.maps.backend.core.ratelimit import rest_read_limiter

__all__ = [
    "Principal",
    "can_configure",
    "can_create_map",
    "can_run_command",
    "get_current_user",
    "principal_from_token",
    "rate_limited_read",
    "require_connection_read",
    "resolve_auth_user",
]

_TICKET_HEADER = "X-Maps-Ticket"
_TICKET_PREFIX = "MapsTicket "


def _extract_ticket(request: Request) -> str:
    # Primary channel: a dedicated header. The SPA is served behind the site
    # Apache, whose default config claims the Authorization header for HTTP
    # Basic auth — so the ticket travels in its own header to avoid the clash.
    ticket = request.headers.get(_TICKET_HEADER)
    if ticket:
        return ticket.strip()
    # Fallback: Authorization: MapsTicket <token> (sites without Basic auth).
    header = request.headers.get("Authorization", "")
    if header.startswith(_TICKET_PREFIX):
        return header[len(_TICKET_PREFIX) :].strip()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing Maps ticket",
    )


async def get_current_user(request: Request) -> Principal:
    """Validate the request's ticket and return the authenticated principal."""
    token = _extract_ticket(request)
    try:
        return validate_ticket(token)
    except InvalidTicket as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Maps ticket",
        ) from exc


def principal_from_token(token: str) -> Principal | None:
    """Validate the reduced-capability stream token from the SSE ``?token=`` param.

    Requires the stream audience, so an API ticket presented here is rejected.
    Returns ``None`` (not a raised 401) so the SSE handler can fail the stream
    cleanly.
    """
    try:
        return validate_stream_ticket(token)
    except InvalidTicket:
        return None


async def rate_limited_read(current_user: Principal = Depends(get_current_user)) -> Principal:
    """Guard the expensive Livestatus readers with a per-user budget.

    Keyed by the authenticated ticket identity (not IP), so a valid ticket can't
    drive unbounded topology / metric-history / search load, and one user's
    flood can't lock out another. See ``rest_read_limiter`` for the budget.
    """
    key = current_user.name
    if rest_read_limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limited",
            headers={"Retry-After": str(int(rest_read_limiter.retry_after(key)) + 1)},
        )
    rest_read_limiter.record(key)
    return current_user


# ---------------------------------------------------------------------------
# Capability predicates (operate purely on the baked-in ticket capabilities)
# ---------------------------------------------------------------------------


def can_configure(principal: Principal) -> bool:
    """Manage connections, images and global settings."""
    return principal.configure


def can_create_map(principal: Principal) -> bool:
    """Create or delete maps — Checkmk's ``general.edit_map`` (per-map edit rights
    are enforced by the GUI on save)."""
    return principal.may_edit


def can_run_command(principal: Principal, action: str) -> bool:
    return principal.may_run_command(action)


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
