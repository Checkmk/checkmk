#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import io
import logging
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import assert_never, Protocol

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.automations.logging import LoggingManager
from cmk.automations.models.helper import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult
from cmk.automations.types import AutomationID
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.automations.automations import AutomationError
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import ConfigCache
from cmk.ccc import version as cmk_version
from cmk.ccc.hostaddress import Hosts
from cmk.checkengine.plugins import AgentBasedPlugins

from ._cache import Cache, CacheError
from ._config import Config, ReloaderConfig
from ._tracer import TRACER


# NOTE: A protocol with a single method can be replaced by a Callable, there is no need for a "self"
# or the concrete name.
class AutomationEngine(Protocol):
    def execute(
        self,
        app: CheckmkBaseApp,
        cmd: AutomationID,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: config.LoadingResult | None,
    ) -> ABCAutomationResult | AutomationError: ...


@dataclass
class _State:
    automation_or_reload_lock: asyncio.Lock
    reload_config: Callable[
        [],
        config.LoadingResult,
    ]
    last_reload_at: float
    plugins: AgentBasedPlugins | None
    loading_result: config.LoadingResult | None
    changes_cache: Cache

    def load(self) -> None:
        """Load the plugins (once) and reload the configuration.

        Raises on failure; callers decide whether to continue or report the error.
        """
        if self.plugins is None:
            self.plugins = config.load_all_plugins()

        # Do not yet set `self.last_reload_at`. We don't know if we succeed.
        time_right_before_reload = time.time()
        self.loading_result = self.reload_config()
        self.last_reload_at = time_right_before_reload

    def reload_if_required(self) -> bool:
        """Reload the configuration if the cache reports a newer change than our last reload.

        Returns whether a reload happened. Raises on failure.
        """
        if self.changes_cache.reload_required(self.last_reload_at):
            self.load()
            return True
        return False


@dataclass(frozen=True)
class _ApplicationDependencies:
    automation_engine: AutomationEngine
    config: Config
    clear_caches_before_each_call: Callable[[ConfigCache, Hosts], None]
    state: _State
    log_manager: LoggingManager


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def make_application(
    *,
    edition: cmk_version.Edition,
    engine: AutomationEngine,
    cache: Cache,
    config: Config,
    reload_config: Callable[
        [],
        config.LoadingResult,
    ],
    clear_caches_before_each_call: Callable[[ConfigCache, Hosts], None],
) -> FastAPI:
    app = FastAPI(
        lifespan=_lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.exception_handler(CacheError)
    async def cache_exception_handler(request: Request, exc: CacheError) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error_code": "CACHE_ERROR",
                "detail": f"Automation cache error: {exc}",
            },
        )

    app.state.dependencies = _ApplicationDependencies(
        automation_engine=engine,
        config=config,
        clear_caches_before_each_call=clear_caches_before_each_call,
        state=_State(
            automation_or_reload_lock=asyncio.Lock(),
            reload_config=reload_config,
            last_reload_at=0,
            plugins=None,
            loading_result=None,
            changes_cache=cache,
        ),
        log_manager=LoggingManager(log_level=logging.NOTSET),
    )

    async def _automation_endpoint(
        request: Request, payload: AutomationPayload
    ) -> AutomationResponse:
        dependencies: _ApplicationDependencies = request.app.state.dependencies
        async with dependencies.state.automation_or_reload_lock:
            return _execute_automation_endpoint(
                edition,
                payload,
                dependencies.automation_engine,
                dependencies.clear_caches_before_each_call,
                dependencies.state,
                dependencies.log_manager,
            )

    app.post("/automation")(_automation_endpoint)
    app.get("/health")(_health_endpoint)

    FastAPIInstrumentor.instrument_app(app)

    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    dependencies: _ApplicationDependencies = app.state.dependencies

    with dependencies.log_manager.file_logging(
        path=dependencies.config.server_config.worker_log,
        log_level=logging.NOTSET,  # Set on logger, not handler
    ):
        logger = dependencies.log_manager.get_logger("automation.reloader")
        # Continue on error. Either the reloader can fix it, or we will raise in the automation endpoint.
        try:
            dependencies.state.load()
        except SystemExit:
            logger.warning("Failed to reload configuration. Shutting down")
        except Exception:
            logger.exception("Error reloading configuration")

        reloader_task = asyncio.create_task(
            _reloader_task(
                config=dependencies.config.reloader_config,
                state=dependencies.state,
                logger=logger,
            )
            if dependencies.config.reloader_config.active
            else asyncio.sleep(0),
        )

        yield

    reloader_task.cancel()


async def _reloader_task(
    config: ReloaderConfig,
    state: _State,
    logger: logging.Logger,
    delayer_factory: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    logger.info("Operational")

    def _get_last_change() -> float:
        try:
            return state.changes_cache.get_last_detected_change()
        except CacheError as error:
            # The CacheError carries all the relevant information we care about. -> Ignore Ruff rule
            logger.error("Error getting last detected change: %(error)s", {"error": error})  # noqa: TRY400
            return 0.0

    # The watcher records a "last detected change" per filesystem event, so a single
    # "activate changes" produces a burst of updates (one per touched file). Reloading
    # on the first event would thrash the workers during bulk changes, so we debounce:
    # poll for a change, then wait for the change stream to go quiet before reloading once.
    while True:
        if (cached_last_change := _get_last_change()) < state.last_reload_at:
            await delayer_factory(config.poll_interval)
            continue

        last_change = cached_last_change
        logger.info(
            "Change detected %(seconds_ago).2f seconds ago",
            {"seconds_ago": time.time() - last_change},
        )

        current_cooldown = config.cooldown_interval
        while True:
            await delayer_factory(current_cooldown)

            cached_last_change = _get_last_change()

            if cached_last_change == last_change:
                async with state.automation_or_reload_lock:
                    # Do not let the reloader fail (and stop).
                    # We will try again on the next change, and report failure in the automation endpoint.
                    try:
                        if state.reload_if_required():
                            logger.info("Triggering reload")
                    except SystemExit:
                        logger.error("Failed to reload configuration. Shutting down")  # noqa: TRY400
                    except Exception:
                        logger.exception("Error reloading configuration")
                    break

            else:
                # More changes arrived mid-cooldown (e.g. a bulk activation still in
                # progress). Wait only for the gap between the two observed changes
                # instead of resetting the full cooldown, so we still reload promptly
                # once the burst settles rather than deferring indefinitely in busy
                # environments (CMK-21331). abs() guards against the timestamp jumping
                # backwards on a cache reset.
                current_cooldown = min(
                    abs(cached_last_change - last_change),
                    config.cooldown_interval,
                )
                last_change = cached_last_change
                logger.info(
                    "Change detected %(seconds_ago).2f seconds ago",
                    {"seconds_ago": time.time() - last_change},
                )


def _execute_automation_endpoint(
    edition: cmk_version.Edition,
    payload: AutomationPayload,
    engine: AutomationEngine,
    clear_caches_before_each_call: Callable[[ConfigCache, Hosts], None],
    state: _State,
    log_manager: LoggingManager,
) -> AutomationResponse:
    logger = log_manager.get_logger("automation")
    logger.info(
        'Processing automation command "%(command)s" with args: %(args)s',
        {"command": payload.name, "args": payload.args},
    )
    try:
        if state.reload_if_required():
            logger.warning("configurations were reloaded due to a stale state.")
    except (Exception, SystemExit) as e:
        return AutomationResponse(
            serialized_result_or_error_code=AutomationError.UNKNOWN_ERROR,
            stdout="",
            stderr=f"Error reloading configuration: {e}",
        )

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
        # Both redirects should be obsolete.
        # All direct write access to STDOUT and STDERR should be replace with logging
        # TODO: Remove the redirects.
        redirect_stdout(buffer_stdout),
        redirect_stderr(buffer_stderr),
        _redirect_stdin(io.StringIO(payload.stdin)),
        log_manager.temporary_log_level(payload.log_level),
        log_manager.stream_logging(stream=buffer_stderr, log_level=logging.ERROR),
    ):
        if state.loading_result:
            clear_caches_before_each_call(
                state.loading_result.config_cache, state.loading_result.hosts_config
            )
        try:
            automation_start_time = time.time()
            result_or_error_code: ABCAutomationResult | int = engine.execute(
                make_app(edition),
                payload.name,
                list(payload.args),
                state.plugins,
                state.loading_result,
            )
            automation_end_time = time.time()
        except SystemExit as system_exit:
            logger.error(  # noqa: TRY400
                'Encountered SystemExit exception while processing automation "%(command)s" with args: %(args)s',
                {"command": payload.name, "args": payload.args},
            )
            result_or_error_code = (
                system_exit_code
                if isinstance(system_exit_code := system_exit.code, int)
                else AutomationError.UNKNOWN_ERROR
            )
        else:
            logger.info(
                'Processed automation command "%(command)s" with args "%(args)s" in %(duration).2f seconds',
                {
                    "command": payload.name,
                    "args": payload.args,
                    "duration": automation_end_time - automation_start_time,
                },
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
