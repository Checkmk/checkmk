#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from fastapi import FastAPI

from cmk.agent_receiver.endpoints import AGENT_RECEIVER_ROUTER, UUID_VALIDATION_ROUTER

from .config import get_config
from .log import configure_logger
from .middleware import B3RequestIDMiddleware
from .relay.app import create_app as create_relay_app
from .relay.app import lifespan as relay_lifespan


def create_sub_app() -> FastAPI:
    app = FastAPI(title="Checkmk Agent Receiver")
    app.add_middleware(B3RequestIDMiddleware)
    app.include_router(AGENT_RECEIVER_ROUTER)
    app.include_router(UUID_VALIDATION_ROUTER)
    return app


def main_app() -> FastAPI:
    # Note: Defining the lifespan on a sub-app does not work as expected. So, it is defined on the
    # main app instead.
    main_app_ = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, lifespan=relay_lifespan)
    config = get_config()

    # Configure logger on the main app level so it works with middleware
    configure_logger(config.log_path)

    # Add middleware to main app BEFORE mounting sub-apps
    main_app_.add_middleware(B3RequestIDMiddleware)

    # Mount the sub-app
    main_app_.mount(f"/{config.site_name}/relays", create_relay_app())
    main_app_.mount(f"/{config.site_name}/agent-receiver", create_sub_app())
    return main_app_
