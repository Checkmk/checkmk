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

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES
from starlette.types import Lifespan

from cmk.fastapi import FastAPI
from cmk.fastapi.request_shape import RequestShapeMiddleware
from cmk.maps.backend.api.v1 import (
    connections,
    maps,
    states,
)
from cmk.maps.backend.connections.base import QueryRefusedError, QueryTimeoutError
from cmk.maps.backend.core.middleware import CompactGZipMiddleware, SecurityHeadersMiddleware
from cmk.maps.backend.core.version import APP_VERSION

# Apache's LimitRequestBody does not cover the proxied /maps/api path, and the
# body is read before the session check, so the daemon bounds it itself. The only
# body it accepts is a map config (at most 5000 objects, no inline images).
MAX_REQUEST_BODY_BYTES = 16 * 1024 * 1024

_HEALTH_PATH = "/api/health"

# Starlette excludes event streams by default. It flushes every chunk on its
# own, though, so a compressed event still reaches the browser at once.
_UNCOMPRESSED_CONTENT_TYPES = tuple(
    t for t in DEFAULT_EXCLUDED_CONTENT_TYPES if t != "text/event-stream"
)


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
        # /maps prefix from Basic auth (Satisfy any) and per-route session auth only
        # guards /api/v1/*, so docs_url/openapi_url would expose the full API schema
        # anonymously. The SPA is the only client and needs no served docs; disabling
        # them also keeps the strict CSP (default-src 'none'; sandbox) honest — the
        # daemon never serves script-bearing HTML (Swagger UI would need script-src).
        # ``app.openapi()`` stays available in-process, which is what the typegen uses.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_REQUEST_BODY_BYTES)
    app.add_middleware(RequestShapeMiddleware, exempt_paths=frozenset({_HEALTH_PATH}))
    app.add_middleware(SecurityHeadersMiddleware)
    # The fastest level: the large states compress almost as well as on the
    # higher ones, and the event stream is compressed once per subscriber.
    app.add_middleware(
        CompactGZipMiddleware,
        minimum_size=1024,
        compresslevel=1,
        exclude_content_types=_UNCOMPRESSED_CONTENT_TYPES,
    )

    app.include_router(maps.router, prefix="/api/v1/maps", tags=["maps"])
    app.include_router(states.router, prefix="/api/v1", tags=["states"])
    app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])

    # The monitoring backend failed, not the daemon: no crash report.
    @app.exception_handler(QueryRefusedError)
    async def _refused(_request: Request, _exc: QueryRefusedError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.BAD_GATEWAY,
            content={"detail": "The monitoring backend refused the query"},
        )

    @app.exception_handler(QueryTimeoutError)
    async def _timed_out(_request: Request, _exc: QueryTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.GATEWAY_TIMEOUT,
            content={"detail": "The monitoring backend did not answer in time"},
        )

    @app.get(_HEALTH_PATH)
    async def health_check() -> dict[str, str]:
        # Reachable anonymously (the /maps prefix is Basic-auth-exempt), so keep it a
        # bare liveness probe — no version or other build detail for an unauth caller.
        return {"status": "ok"}

    return app
