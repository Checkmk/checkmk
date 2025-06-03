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
from typing import assert_never, Protocol

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.ccc import tty
from cmk.ccc import version as cmk_version

from cmk.utils import paths
from cmk.utils.log import logger as cmk_logger

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult

from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base import config
from cmk.base.automations import AutomationError
from cmk.base.config import ConfigCache

from ._cache import Cache, CacheError
from ._config import ReloaderConfig
from ._log import LOGGER, temporary_log_level
from ._tracer import TRACER


class AutomationEngine(Protocol):
    def execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: config.LoadingResult | None,
    ) -> ABCAutomationResult | AutomationError: ...


@dataclass
class _State:
    automation_or_reload_lock: asyncio.Lock
    last_reload_at: float
    plugins: AgentBasedPlugins | None
    loading_result: config.LoadingResult | None


@dataclass(frozen=True)
class _ApplicationDependencies:
    automation_engine: AutomationEngine
    changes_cache: Cache
    reloader_config: ReloaderConfig
    reload_config: Callable[[AgentBasedPlugins], config.LoadingResult]
    clear_caches_before_each_call: Callable[[ConfigCache], None]
    state: _State


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def make_application(
    *,
    engine: AutomationEngine,
    cache: Cache,
    reloader_config: ReloaderConfig,
    reload_config: Callable[[AgentBasedPlugins], config.LoadingResult],
    clear_caches_before_each_call: Callable[[ConfigCache], None],
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
            plugins=None,
            loading_result=None,
        ),
    )

    app.post("/automation")(_automation_endpoint)
    app.get("/health")(_health_endpoint)

    FastAPIInstrumentor.instrument_app(app)

    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    dependencies: _ApplicationDependencies = app.state.dependencies
    dependencies.state.last_reload_at = time.time()

    plugins = config.load_all_pluginX(paths.checks_dir)
    dependencies.state.plugins = plugins

    tty.reinit()
    dependencies.state.loading_result = dependencies.reload_config(plugins)

    reloader_task = asyncio.create_task(
        _reloader_task(
            config=dependencies.reloader_config,
            cache=dependencies.changes_cache,
            reload_callback=lambda: dependencies.reload_config(plugins),
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
    reload_callback: Callable[[], config.LoadingResult],
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
                    state.loading_result = reload_callback()
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
    reload_config: Callable[[AgentBasedPlugins], config.LoadingResult],
    clear_caches_before_each_call: Callable[[ConfigCache], None],
    state: _State,
) -> AutomationResponse:
    LOGGER.info(
        '[automation] Processing automation command "%s" with args: %s',
        payload.name,
        payload.args,
    )
    if cache.reload_required(state.last_reload_at):
        state.last_reload_at = time.time()
        if not state.plugins:
            # This should never happen. AFAICS, we have to make the plugins optional,
            # because we don't want to load them when the `state` is first instantiated,
            # but at a later point. This is a bit of a code smell, but I don't see a better
            # way to do this right now.
            # We could intialize the `state` with `AgentBasedPlugins.empty()` but that would
            # bare the risk of accidentally operating with the empty set of plugins.
            raise RuntimeError("Plugins are not loaded yet")
        state.loading_result = reload_config(state.plugins)
        LOGGER.warning("[automation] configurations were reloaded due to a stale state.")

    buffer_stdout = io.StringIO()
    buffer_stderr = io.StringIO()
    with (
        TRACER.span(
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
        if state.loading_result:
            clear_caches_before_each_call(state.loading_result.config_cache)
        try:
            automation_start_time = time.time()
            result_or_error_code: ABCAutomationResult | int = engine.execute(
                payload.name,
                list(payload.args),
                state.plugins,
                state.loading_result,
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
