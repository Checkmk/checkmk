#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from fastapi import FastAPI

from cmk.agent_receiver.agent_receiver.endpoints import (
    AGENT_RECEIVER_ROUTER,
    UUID_VALIDATION_ROUTER,
)
from cmk.agent_receiver.lib.middleware import B3RequestIDMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Checkmk Agent Receiver")
    app.add_middleware(B3RequestIDMiddleware)
    app.include_router(AGENT_RECEIVER_ROUTER)
    app.include_router(UUID_VALIDATION_ROUTER)
    return app
