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

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.ccc import version as cmk_version

from cmk.utils import paths, tty
from cmk.utils.caching import cache_manager
from cmk.utils.log import logger as cmk_logger

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult

from cmk.base import config
from cmk.base.automations import AutomationError

from ._cache import Cache, CacheError
from ._config import ReloaderConfig
from ._log import LOGGER, temporary_log_level
from ._tracer import TRACER


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def reload_automation_config() -> None:
    cache_manager.clear()
    config.load(validate_hosts=False)


def clear_caches_before_each_call() -> None:
    config.get_config_cache().ruleset_matcher.clear_caches()


@contextmanager
def redirect_stdin(stream: io.StringIO) -> Iterator[None]:
    orig_stdin = sys.stdin
    try:
        sys.stdin = stream
        yield
    finally:
        sys.stdin = orig_stdin


class AutomationEngine(Protocol):
    def execute(
        self,
        cmd: str,
        args: list[str],
        *,
        called_from_automation_helper: bool,
    ) -> ABCAutomationResult | AutomationError: ...


def get_application(
    *,
    engine: AutomationEngine,
    cache: Cache,
    reloader_config: ReloaderConfig,
    reload_config: Callable[[], None],
    clear_caches_before_each_call: Callable[[], None],
) -> FastAPI:
    state = _State(
        automation_or_reload_lock=asyncio.Lock(),
        last_reload_at=0,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        # Setting the access log format via config did not work as intended with uvicorn. This
        # seems to be a known issue: https://github.com/encode/uvicorn/issues/527
        for handler in getLogger("uvicorn.access").handlers:
            handler.setFormatter(Formatter("%(asctime)s %(message)s"))

        state.last_reload_at = time.time()
        config.load_all_plugins(
            local_checks_dir=paths.local_checks_dir, checks_dir=paths.checks_dir
        )
        tty.reinit()
        reload_config()

        reloader_task = asyncio.create_task(
            _reloader_task(
                config=reloader_config,
                cache=cache,
                reload_callback=reload_config,
                state=state,
            )
            if reloader_config.active
            else asyncio.sleep(0),
        )

        yield

        reloader_task.cancel()

    app = FastAPI(lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None)

    FastAPIInstrumentor.instrument_app(app)

    @app.post("/automation")
    async def automation(payload: AutomationPayload) -> AutomationResponse:
        async with state.automation_or_reload_lock:
            return _execute_automation_endpoint(
                payload,
                engine,
                cache,
                reload_config,
                clear_caches_before_each_call,
                state,
            )

    @app.get("/health")
    async def check_health() -> HealthCheckResponse:
        return HealthCheckResponse(last_reload_at=state.last_reload_at)

    return app


@dataclass
class _State:
    automation_or_reload_lock: asyncio.Lock
    last_reload_at: float


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
        TRACER.span(
            f"automation[{payload.name}]",
            attributes={
                "cmk.automation.name": payload.name,
                "cmk.automation.args": payload.args,
            },
        ),
        redirect_stdout(buffer_stdout),
        redirect_stderr(buffer_stderr),
        redirect_stdin(io.StringIO(payload.stdin)),
        temporary_log_level(cmk_logger, payload.log_level),
    ):
        clear_caches_before_each_call()
        try:
            result_or_error_code: ABCAutomationResult | int = engine.execute(
                payload.name,
                list(payload.args),
                called_from_automation_helper=True,
            )
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
                '[automation] Processed automation command "%s" with args: %s',
                payload.name,
                payload.args,
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
