#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, AsyncExitStack

from fastapi import FastAPI

from cmk.agent_receiver.lib.certs import agent_root_ca, relay_root_ca
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import configure_logger
from cmk.agent_receiver.lib.middleware import B3RequestIDMiddleware
from cmk.ccc.version import edition
from cmk.licensing.basics.options import get_license_options

from .agent_receiver.app import create_app as create_ar_app
from .relay.api.routers.relays.dependencies import LifespanState
from .relay.api.routers.relays.handlers import ForwardMonitoringDataHandler
from .relay.app import create_app as create_relay_app
from .relay.app import lifespan as relay_lifespan


def _lifespan(
    relay_enabled: bool,
) -> Callable[[FastAPI], AbstractAsyncContextManager[LifespanState]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[LifespanState]:
        # Loading a CA parses its private key, a few 100 ms of CPU for 4096 bits. Here it
        # delays the start of the worker instead of stalling its first requests.
        agent_root_ca()
        relay_root_ca()
        config = get_config()
        async with AsyncExitStack() as stack:
            forwarder = await stack.enter_async_context(
                ForwardMonitoringDataHandler(
                    data_socket=config.raw_data_socket, socket_timeout=config.socket_timeout
                ).running()
            )
            if relay_enabled:
                await stack.enter_async_context(relay_lifespan(app))
            yield LifespanState(forward_monitoring_data_handler=forwarder)

    return lifespan


def main_app() -> FastAPI:
    config = get_config()
    relay_enabled = get_license_options(config.omd_root, edition(config.omd_root)).relay.enabled

    # Note: Defining the lifespan on a sub-app does not work as expected. So, it is defined on the
    # main app instead.
    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=_lifespan(relay_enabled),
    )

    # Configure logger on the main app level so it works with middleware
    configure_logger(config.log_path)

    # Add middleware to main app BEFORE mounting sub-apps
    main_app_.add_middleware(B3RequestIDMiddleware)

    # Mount the sub-app
    main_app_.mount(f"/{config.site_name}/relays", create_relay_app())
    main_app_.mount(f"/{config.site_name}/agent-receiver", create_ar_app())
    return main_app_
