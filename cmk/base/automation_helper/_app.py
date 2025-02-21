#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import io
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from logging import Formatter, getLogger
from typing import assert_never, Protocol

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.ccc import version as cmk_version

from cmk.utils import paths, tty
from cmk.utils.log import logger as cmk_logger

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult

from cmk.base import config
from cmk.base.automations import AutomationError

from ._cache import Cache, CacheError
from ._config import ReloaderConfig
from ._log import LOGGER, temporary_log_level
from ._tracer import TRACER


class AutomationEngine(Protocol):
    def execute(
        self,
        cmd: str,
        args: list[str],
        *,
        called_from_automation_helper: bool,
    ) -> ABCAutomationResult | AutomationError: ...


@dataclass
class _State:
    automation_or_reload_lock: asyncio.Lock
    last_reload_at: float


@dataclass(frozen=True)
class _ApplicationDependencies:
    automation_engine: AutomationEngine
    changes_cache: Cache
    reloader_config: ReloaderConfig
    reload_config: Callable[[], None]
    clear_caches_before_each_call: Callable[[], None]
    state: _State


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def make_application(
    *,
    engine: AutomationEngine,
    cache: Cache,
    reloader_config: ReloaderConfig,
    reload_config: Callable[[], None],
    clear_caches_before_each_call: Callable[[], None],
) -> FastAPI:
    app = FastAPI(
        lifespan=_lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.dependencies = _ApplicationDependencies(
        automation_engine=engine,
        changes_cache=cache,
        reloader_config=reloader_config,
        reload_config=reload_config,
        clear_caches_before_each_call=clear_caches_before_each_call,
        state=_State(
            automation_or_reload_lock=asyncio.Lock(),
            last_reload_at=0,
        ),
    )

    app.post("/automation")(_automation_endpoint)
    app.get("/health")(_health_endpoint)

    FastAPIInstrumentor.instrument_app(app)

    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Setting the access log format via config did not work as intended with uvicorn. This
    # seems to be a known issue: https://github.com/encode/uvicorn/issues/527
    for handler in getLogger("uvicorn.access").handlers:
        handler.setFormatter(Formatter("%(asctime)s %(message)s"))

    dependencies: _ApplicationDependencies = app.state.dependencies
    dependencies.state.last_reload_at = time.time()
    config.load_all_plugins(local_checks_dir=paths.local_checks_dir, checks_dir=paths.checks_dir)
    tty.reinit()
    dependencies.reload_config()

    reloader_task = asyncio.create_task(
        _reloader_task(
            config=dependencies.reloader_config,
            cache=dependencies.changes_cache,
            reload_callback=dependencies.reload_config,
            state=dependencies.state,
        )
        if dependencies.reloader_config.active
        else asyncio.sleep(0),
    )

    yield

    reloader_task.cancel()


async def _reloader_task(
    config: ReloaderConfig,
    cache: Cache,
    reload_callback: Callable[[], None],
    state: _State,
    delayer_factory: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    LOGGER.info("[reloader] Operational")
    while True:
        if (cached_last_change := _retrieve_last_change(cache)) < state.last_reload_at:
            await delayer_factory(config.poll_interval)
            continue

        last_change = cached_last_change
        LOGGER.info(
            "[reloader] Change detected %.2f seconds ago",
            time.time() - last_change,
        )

        current_cooldown = config.cooldown_interval
        while True:
            await delayer_factory(current_cooldown)

            cached_last_change = _retrieve_last_change(cache)

            if cached_last_change == last_change:
                async with state.automation_or_reload_lock:
                    if cached_last_change < state.last_reload_at:
                        break

                    LOGGER.info("[reloader] Triggering reload")
                    state.last_reload_at = time.time()
                    reload_callback()
                    break

            else:
                current_cooldown = min(
                    # be rebust against cache resets, just in case
                    abs(cached_last_change - last_change),
                    config.cooldown_interval,
                )
                last_change = cached_last_change
                LOGGER.info(
                    "[reloader] Change detected %.2f seconds ago",
                    time.time() - last_change,
                )


def _retrieve_last_change(cache: Cache) -> float:
    try:
        return cache.get_last_detected_change()
    except CacheError as err:
        LOGGER.error("[reloader] Cache failure", exc_info=err)
        return 0


async def _automation_endpoint(request: Request, payload: AutomationPayload) -> AutomationResponse:
    dependencies: _ApplicationDependencies = request.app.state.dependencies
    async with dependencies.state.automation_or_reload_lock:
        return _execute_automation_endpoint(
            payload,
            dependencies.automation_engine,
            dependencies.changes_cache,
            dependencies.reload_config,
            dependencies.clear_caches_before_each_call,
            dependencies.state,
        )


def _execute_automation_endpoint(
    payload: AutomationPayload,
    engine: AutomationEngine,
    cache: Cache,
    reload_config: Callable[[], None],
    clear_caches_before_each_call: Callable[[], None],
    state: _State,
) -> AutomationResponse:
    LOGGER.info(
        '[automation] Processing automation command "%s" with args: %s',
        payload.name,
        payload.args,
    )
    if cache.reload_required(state.last_reload_at):
        state.last_reload_at = time.time()
        reload_config()
        LOGGER.warning("[automation] configurations were reloaded due to a stale state.")

    buffer_stdout = io.StringIO()
    buffer_stderr = io.StringIO()
    with (
        TRACER.start_as_current_span(
            f"automation[{payload.name}]",
            attributes={
                "cmk.automation.name": payload.name,
                "cmk.automation.args": payload.args,
            },
        ),
        redirect_stdout(buffer_stdout),
        redirect_stderr(buffer_stderr),
        _redirect_stdin(io.StringIO(payload.stdin)),
        temporary_log_level(cmk_logger, payload.log_level),
    ):
        clear_caches_before_each_call()
        try:
            automation_start_time = time.time()
            result_or_error_code: ABCAutomationResult | int = engine.execute(
                payload.name,
                list(payload.args),
                called_from_automation_helper=True,
            )
            automation_end_time = time.time()
        except SystemExit as system_exit:
            LOGGER.error(
                '[automation] Encountered SystemExit exception while processing automation "%s" with args: %s',
                payload.name,
                payload.args,
            )
            result_or_error_code = (
                system_exit_code
                if isinstance(system_exit_code := system_exit.code, int)
                else AutomationError.UNKNOWN_ERROR
            )
        else:
            LOGGER.info(
                '[automation] Processed automation command "%s" with args "%s" in %.2f seconds',
                payload.name,
                payload.args,
                automation_end_time - automation_start_time,
            )

        match result_or_error_code:
            case ABCAutomationResult():
                return AutomationResponse(
                    serialized_result_or_error_code=result_or_error_code.serialize(
                        cmk_version.Version.from_str(cmk_version.__version__)
                    ),
                    stdout=buffer_stdout.getvalue(),
                    stderr=buffer_stderr.getvalue(),
                )

            case int():
                return AutomationResponse(
                    serialized_result_or_error_code=result_or_error_code,
                    stdout=buffer_stdout.getvalue(),
                    stderr=buffer_stderr.getvalue(),
                )

            case _:
                assert_never(result_or_error_code)


@contextmanager
def _redirect_stdin(stream: io.StringIO) -> Iterator[None]:
    orig_stdin = sys.stdin
    try:
        sys.stdin = stream
        yield
    finally:
        sys.stdin = orig_stdin


async def _health_endpoint(request: Request) -> HealthCheckResponse:
    dependencies: _ApplicationDependencies = request.app.state.dependencies
    return HealthCheckResponse(last_reload_at=dependencies.state.last_reload_at)
