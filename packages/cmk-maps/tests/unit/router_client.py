#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types of the ``router_client`` fixture shared by the Maps daemon route tests."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import APIRouter
from fastapi.testclient import TestClient

from cmk.maps.backend.core.auth import GuiAuth, Principal

# A dependency the route tests resolve to a fixed value instead: the user from the
# session (``deps.get_current_user``), the owner the GUI names for a map
# (``deps.get_map_owner``), or a guard chained onto the user
# (``deps.rate_limited_read``, ``deps.require_connection_read``).
type AuthDependency = (
    Callable[[str, GuiAuth], Awaitable[Principal]]
    | Callable[[str, GuiAuth, Principal], Awaitable[str | None]]
    | Callable[[Principal], Awaitable[Principal]]
)


class RouterClientFactory(Protocol):
    """Builds a ``TestClient`` for a single router with auth overrides."""

    def __call__(
        self,
        router: APIRouter,
        prefix: str,
        *,
        overrides: dict[AuthDependency, object] | None = None,
    ) -> TestClient: ...
