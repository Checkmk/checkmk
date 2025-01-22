#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from cmk.gui.background_job import HealthResponse


def get_application(loaded_at: int) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.state.loaded_at = loaded_at

    FastAPIInstrumentor.instrument_app(app)

    @app.get("/health")
    async def check_health(request: Request) -> HealthResponse:
        return HealthResponse(loaded_at=request.app.state.loaded_at)

    return app
