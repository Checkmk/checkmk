#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request-layer wiring tests for the guard dependencies (``api/v1/deps``).

The pure capability predicates are unit-tested in ``test_deps.py``; here we mount
a tiny route behind each guard and assert the 200/403 decision at the request
layer, plus the real ``get_current_user`` 401 path for a missing ticket.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from cmk.maps.backend.api.v1 import deps
from cmk.maps.backend.core.auth import Principal

_Guard = Callable[[Principal], Awaitable[Principal]]

# The daemon's only capability guard. ``configure`` and ``may_edit`` themselves
# gate no route directly (the sole mutating endpoint, ``POST /register``, is
# ticket-authenticated with its own ownership checks); both merely broaden
# read access to the connection list, which this guard admits.
_GUARDS: dict[str, _Guard] = {
    "connection-read": deps.require_connection_read,
}

# Capabilities that satisfy / fail the guard.
_CONFIGURER = Principal(name="cfg", configure=True)
_MAP_CREATOR = Principal(name="creator", may_edit=True)
# Neither configure nor edit: a read-only viewer that must fail the guard.
_VIEW_ONLY = Principal(name="viewer")


def _guarded_app(guard: _Guard) -> FastAPI:
    async def _probe(_: Principal = Depends(guard)) -> dict[str, bool]:
        return {"ok": True}

    router = APIRouter()
    # add_api_route is a plain typed method call — unlike the @router.get
    # decorator, which mypy rejects under disallow_untyped_decorators.
    router.add_api_route("/probe", _probe, methods=["GET"])
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.parametrize(
    "principal",
    [
        pytest.param(_CONFIGURER, id="connection-read-configurer"),
        pytest.param(_MAP_CREATOR, id="connection-read-creator"),
    ],
)
def test_guard_allows_authorised_principal(principal: Principal) -> None:
    app = _guarded_app(_GUARDS["connection-read"])
    app.dependency_overrides[deps.get_current_user] = lambda: principal
    with TestClient(app) as client:
        resp = client.get("/probe")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_guard_forbids_view_only_principal() -> None:
    app = _guarded_app(_GUARDS["connection-read"])
    app.dependency_overrides[deps.get_current_user] = lambda: _VIEW_ONLY
    with TestClient(app) as client:
        resp = client.get("/probe")
    assert resp.status_code == 403


def test_guard_rejects_missing_ticket_with_401() -> None:
    # No auth override: the real get_current_user runs and there is no ticket
    # header, so the request is rejected before the capability check.
    app = _guarded_app(_GUARDS["connection-read"])
    with TestClient(app) as client:
        resp = client.get("/probe")
    assert resp.status_code == 401
