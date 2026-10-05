#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types of the ``router_client`` fixture shared by the Maps daemon route tests."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import APIRouter, Request
from fastapi.testclient import TestClient

from cmk.maps.backend.core.auth import Principal

# A guard dependency is either ticket-authenticating off the request
# (``deps.get_current_user``) or chained onto the principal it resolved
# (``deps.rate_limited_read``, ``deps.require_connection_read``).
AuthDependency = (
    Callable[[Request], Awaitable[Principal]] | Callable[[Principal], Awaitable[Principal]]
)


class RouterClientFactory(Protocol):
    """Builds a ``TestClient`` for a single router with auth overrides."""

    def __call__(
        self,
        router: APIRouter,
        prefix: str,
        *,
        overrides: dict[AuthDependency, Principal] | None = None,
    ) -> TestClient: ...
