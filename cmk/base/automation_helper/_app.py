#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import io
import logging
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import assert_never, Protocol

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.automations.logging import LoggingManager
from cmk.automations.models.helper import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult
from cmk.automations.types import AutomationID
from cmk.base.automations.automations import AutomationError
from cmk.ccc import version as cmk_version

from ._cache import Cache, CacheError
from ._config import Config, ReloaderConfig
from ._tracer import TRACER


class AutomationEngine(Protocol):
    def update(self, omd_root: Path, raw_config: Mapping[str, object]) -> None: ...

    def execute(
        self, cmd: AutomationID, args: list[str]
    ) -> ABCAutomationResult | AutomationError: ...


@dataclass
class _State:
    engine: AutomationEngine
    omd_root: Path
    reload_config: Callable[[], Mapping[str, object]]
    last_reload_at: float
    changes_cache: Cache
    _busy: bool = field(default=False, init=False)

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Guard automations and reloads, which must never overlap.

        They are serialized by running synchronously on the worker's event loop thread.
        Fail loudly if they run elsewhere (e.g. a plain `def` endpoint, which FastAPI runs
        in a threadpool) or overlap (e.g. because the guarded work awaits).
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                "Automations and reloads must run on the event loop thread"
            ) from None
        if self._busy:
            raise RuntimeError("Automations and reloads must not overlap")
        self._busy = True
        try:
            yield
        finally:
            self._busy = False

    def load(self) -> None:
        """Reload the configuration and hand it to the engine.

        Raises on failure; callers decide whether to continue or report the error.
        """
        # Do not yet set `self.last_reload_at`. We don't know if we succeed.
        time_right_before_reload = time.time()
        self.engine.update(self.omd_root, self.reload_config())
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
    config: Config
    state: _State
    log_manager: LoggingManager


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def make_application(
    *,
    omd_root: Path,
    engine: AutomationEngine,
    cache: Cache,
    config: Config,
    reload_config: Callable[[], Mapping[str, object]],
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
        config=config,
        state=_State(
            engine=engine,
            omd_root=omd_root,
            reload_config=reload_config,
            last_reload_at=0,
            changes_cache=cache,
        ),
        log_manager=LoggingManager(log_level=logging.NOTSET),
    )

    async def _automation_endpoint(
        request: Request, payload: AutomationPayload
    ) -> AutomationResponse:
        dependencies: _ApplicationDependencies = request.app.state.dependencies
        with dependencies.state.exclusive():
            return _execute_automation_endpoint(
                payload,
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
        with dependencies.state.exclusive():
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
        # Nobody awaits the reloader, so log if it dies instead of letting it stop silently.
        reloader_task.add_done_callback(lambda task: _log_reloader_crash(task, logger))

        yield

    reloader_task.cancel()


def _log_reloader_crash(task: asyncio.Task[None], logger: logging.Logger) -> None:
    if not task.cancelled() and (error := task.exception()) is not None:
        logger.critical("Reloader stopped", exc_info=error)


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
                with state.exclusive():
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
    payload: AutomationPayload,
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
        try:
            automation_start_time = time.time()
            result_or_error_code: ABCAutomationResult | int = state.engine.execute(
                payload.name, list(payload.args)
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
