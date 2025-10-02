#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from cmk.agent_receiver.relay.api.routers.base_router import RELAY_ROUTER

# NOTE: The import below is a hack, we should register endpoints explicitly!
from . import endpoints as endpoints
from .apps_and_routers import AGENT_RECEIVER_APP, UUID_VALIDATION_ROUTER
from .config import get_config
from .log import configure_logger, logger
from .middleware import B3RequestIDMiddleware
from .relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from .relay.api.routers.tasks.libs.tasks_repository import TasksRepository
from .relay.lib.relays_repository import RelaysRepository


def _build_config_task_factory() -> ConfigTaskFactory:
    # We have dependency getter but they depend on request context. So this code is similar to
    # those getters.
    # TODO: Question. Shall we improve those getters and remove the get_config dependency?
    # Which does not depend on request context.
    config = get_config()
    tasks_repository = TasksRepository(
        ttl_seconds=config.task_ttl,
        max_tasks_per_relay=config.max_tasks_per_relay,
    )
    relays_repository = RelaysRepository.from_site(config.site_url, config.site_name)
    return ConfigTaskFactory(
        relays_repository=relays_repository,
        tasks_repository=tasks_repository,
    )


async def _send_config_to_relays() -> None:
    """Execute one-off startup tasks after the application is ready.

    Currently this enqueues a RelayConfig task for every known relay by
    invoking ConfigTaskFactory.process().
    """
    factory = _build_config_task_factory()
    # TODO: Question: What about exception handling? Let it die and crash the app or log and continue?
    created = factory.process()
    logger.info(
        "startup: created %d config task(s) for %d relay(s)",
        len(created),
        len({t.id for t in created}),
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001 (FastAPI signature)
    # Startup phase
    await _send_config_to_relays()
    yield
    # Shutdown phase (currently nothing to do)


def main_app() -> FastAPI:
    # Create main app first
    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=_lifespan,
    )

    config = get_config()

    # Configure logger on the main app level so it works with middleware
    configure_logger(config.log_path)

    # Add middleware to main app BEFORE mounting sub-apps
    main_app_.add_middleware(B3RequestIDMiddleware)

    # this must happen *after* registering the endpoints
    AGENT_RECEIVER_APP.include_router(UUID_VALIDATION_ROUTER)
    AGENT_RECEIVER_APP.include_router(RELAY_ROUTER)

    # Mount the sub-app
    main_app_.mount(f"/{config.site_name}/agent-receiver", AGENT_RECEIVER_APP)
    return main_app_
