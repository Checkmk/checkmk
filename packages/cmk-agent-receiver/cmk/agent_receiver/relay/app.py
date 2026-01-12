#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import logger
from cmk.agent_receiver.lib.middleware import B3RequestIDMiddleware
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TasksRepository
from cmk.agent_receiver.relay.lib.relays_repository import CheckmkAPIError, RelaysRepository
from cmk.ccc import version as cmk_version

from .api.routers.relays import router as relay_router
from .api.routers.tasks import router as task_router


def _build_config_task_factory() -> ConfigTaskFactory:
    config = get_config()
    tasks_repository = TasksRepository(
        ttl_seconds=config.task_ttl,
        max_pending_tasks_per_relay=config.max_pending_tasks_per_relay,
    )
    relays_repository = RelaysRepository.from_site(
        config.rest_api_url, config.site_name, config.helper_config_dir
    )
    return ConfigTaskFactory(
        relays_repository=relays_repository,
        tasks_repository=tasks_repository,
    )


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=0.5, max=5),
    retry=retry_if_exception_type(CheckmkAPIError),
    before_sleep=lambda retry_state: logger.info(
        "Failed to send config to relays (attempt %d): %s. Retrying in %.2f seconds...",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "Unknown error",
        retry_state.next_action.sleep if retry_state.next_action else 0,
    ),
    reraise=True,
)
async def _build_config_for_relays() -> None:
    """Enqueue initial relay config tasks."""
    factory = _build_config_task_factory()
    created = factory.create_for_all_relays()
    logger.info(
        "startup: created %d config task(s) for %d relay(s)",
        len(created),
        len({t.relay_id for t in created}),
    )


def _schedule_initial_relay_config() -> None:
    """Schedule of the initial relay configuration task.

    IMPORTANT: We intentionally do not await the task here. Awaiting would block
    FastAPI's startup phase and delay readiness of the agent receiver until all
    retries against the Checkmk site API have succeeded or exhausted.

    Instead we schedule it on the running loop and attach a done callback that
    logs any terminal failure. This keeps behaviour (attempt with retries) but
    makes startup non-blocking for site creation / health checks.
    """
    task = asyncio.create_task(
        _build_config_for_relays(), name="agent-receiver-initial-relay-config"
    )

    def _log_result(t: asyncio.Task[None]) -> None:
        try:
            t.result()
        except Exception as exc:
            logger.warning(
                "startup: initial relay config task failed after retries: %s", exc, exc_info=True
            )
        else:
            logger.info("startup: initial relay config task finished successfully")

    task.add_done_callback(_log_result)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """App lifespan:
    1. Schedule (non-blocking) background relay config task if edition supports relays.
    """
    if cmk_version.edition_supports_relay(cmk_version.edition(get_config().omd_root)):
        _schedule_initial_relay_config()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Checkmk Relay",
    )
    app.add_middleware(B3RequestIDMiddleware)
    app.include_router(relay_router)
    app.include_router(task_router)
    return app
