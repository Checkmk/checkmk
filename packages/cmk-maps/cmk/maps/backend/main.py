#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk Maps backend — FastAPI application entry point.

The routed application itself is built by :mod:`cmk.maps.backend.app`; what is
added here is everything that only makes sense inside a running OMD site —
logging, tracing, crash reporting and the startup lifespan. Importing this
module is therefore not free of side effects, which is why the schema dump goes
through the factory instead.

In-tree the daemon runs inside the OMD site behind the site Apache. It performs
no login, session or password handling of its own: requests are authenticated by
the GUI session cookie, which the daemon has the GUI check (see
:mod:`cmk.maps.backend.core.auth`). The browser sends that cookie with a request
another site makes it send, too, so such requests are refused before routing.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from cmk import trace
from cmk.ccc.log import CMKFormatter
from cmk.ccc.site import get_omd_config, omd_site
from cmk.fastapi.gui_session import GuiLoopback, loopback_http_client
from cmk.maps.backend.app import create_app
from cmk.maps.backend.core.auth import GuiAuth
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.core.crash import create_crash_report
from cmk.maps.backend.core.version import APP_VERSION
from cmk.maps.backend.services import connection_service, settings_service
from cmk.maps.backend.services.state_service import list_connection_ids
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.trace.logs import add_span_log_handler

logger = logging.getLogger(__name__)


def _init_logging() -> None:
    """Configure the root logger for the worker process.

    Done at startup rather than at import so that importing the daemon (the
    schema dump, tests) leaves the caller's logging setup alone.
    """
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(CMKFormatter())
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        handlers=[handler],
    )


def _init_tracing() -> None:
    """Wire the worker into Checkmk's OpenTelemetry setup (like the other
    site daemons): spans are exported per the site's trace-send config and
    span logs ride the regular logging."""
    omd_root = Path(settings.checkmk_omd_root)
    init_span_processor(
        trace.init_tracing(
            service_namespace="",
            service_name="cmk-maps",
            service_instance_id=omd_site(),
            extra_resource_attributes=trace.resource_attributes_from_config(omd_root),
        ),
        exporter_from_config(
            exporter_log_level=logging.ERROR,
            config=trace.trace_send_config(get_omd_config(omd_root)),
        ),
    )
    add_span_log_handler()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _init_logging()

    logger.info(
        "Starting Checkmk Maps backend %(version)s for site '%(site)s'",
        {"version": APP_VERSION, "site": settings.checkmk_site},
    )

    _init_tracing()

    settings_service.apply_log_level(settings_service.get_system_settings().log_level)

    # Connections come from the WATO ``maps_connections`` global (read-only);
    # connection_service falls back to a built-in local-site connection when none
    # are configured, so there is always a usable data source.
    connection_service.activate_all()

    # Fail fast: the daemon exists to serve live monitoring data, so coming up
    # with no usable Livestatus connection (e.g. the primary failed to register)
    # must fail the worker rather than serve empty maps behind a healthy
    # /api/health.
    if not list_connection_ids():
        raise RuntimeError(
            "No Livestatus connection registered; aborting startup — check the "
            "monitoring core socket and the Maps connections global setting"
        )

    warmup_task = asyncio.create_task(connection_service.warmup_loop())
    try:
        async with loopback_http_client(Path(settings.checkmk_omd_root)) as http:
            app.state.gui_auth = GuiAuth(GuiLoopback(http))
            yield
    finally:
        logger.info("Shutting down Checkmk Maps backend.")
        warmup_task.cancel()
        with suppress(asyncio.CancelledError):
            await warmup_task


app = create_app(lifespan=lifespan)


@app.exception_handler(Exception)
async def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Persist unhandled request exceptions as Checkmk crash reports.

    HTTPExceptions and validation errors have their own handlers; only real
    bugs end up here. The crash ID in the response lets an operator find the
    report on the site's crash reports page.
    """
    try:
        crash_id = create_crash_report(Path(settings.checkmk_omd_root))
    except Exception:
        logger.exception("Failed to write the crash report for the following exception")
        crash_id = "n/a"
    logger.error(
        "Unhandled exception on %(path)s (crash ID: %(crash_id)s)",
        {"path": request.url.path, "crash_id": crash_id},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "crash_id": crash_id},
    )


# A span over a long-lived stream is of little value.
FastAPIInstrumentor.instrument_app(app, excluded_urls="sse/maps")
