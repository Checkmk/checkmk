#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Application factory for the Checkmk Maps backend.

Separate from :mod:`cmk.maps.backend.main` so that building the application is
free of site and process state: the build dumps ``create_app().openapi()`` to
generate the SPA's daemon types, and that action runs outside an OMD site and
must not reconfigure logging or install tracing instrumentation. Everything
that touches the running site lives in :mod:`cmk.maps.backend.main`.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.types import Lifespan

from cmk.maps.backend.api.v1 import (
    connections,
    maps,
    states,
)
from cmk.maps.backend.core.middleware import SecurityHeadersMiddleware
from cmk.maps.backend.core.version import APP_VERSION


def create_app(*, lifespan: Lifespan[FastAPI] | None = None) -> FastAPI:
    """Build the routed application.

    The routes and their models are the whole of the daemon's API contract, so
    the schema this yields is the same one the daemon serves at runtime. Only
    the startup lifespan differs: the schema dump passes none.
    """
    app = FastAPI(
        title="Checkmk Maps API",
        version=APP_VERSION,
        description="REST API for Checkmk Maps — monitoring visualization",
        lifespan=lifespan,
        # No interactive docs / OpenAPI schema. The site Apache exempts the whole
        # /maps prefix from Basic auth (Satisfy any) and per-route ticket auth only
        # guards /api/v1/*, so docs_url/openapi_url would expose the full API schema
        # anonymously. The SPA is the only client and needs no served docs; disabling
        # them also keeps the strict CSP (default-src 'none'; sandbox) honest — the
        # daemon never serves script-bearing HTML (Swagger UI would need script-src).
        # ``app.openapi()`` stays available in-process, which is what the typegen uses.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.include_router(maps.router, prefix="/api/v1/maps", tags=["maps"])
    app.include_router(states.router, prefix="/api/v1", tags=["states"])
    app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        # Reachable anonymously (the /maps prefix is Basic-auth-exempt), so keep it a
        # bare liveness probe — no version or other build detail for an unauth caller.
        return {"status": "ok"}

    return app
