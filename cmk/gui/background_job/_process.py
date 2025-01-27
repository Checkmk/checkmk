#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Background job process entry point.

This must not be imported from anywhere outside of the background job process."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from logging import Formatter, Logger, StreamHandler
from pathlib import Path
from typing import ContextManager, IO

from setproctitle import setthreadtitle

from cmk.ccc import store
from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import edition

from cmk.utils import paths
from cmk.utils.log import VERBOSE
from cmk.utils.user import UserId

from cmk.gui import log
from cmk.gui.crash_handler import create_gui_crash_report
from cmk.gui.features import features_registry
from cmk.gui.i18n import _
from cmk.gui.session import SuperUserContext, UserContext
from cmk.gui.single_global_setting import load_gui_log_levels
from cmk.gui.utils import get_failed_plugins

from cmk.trace import (
    get_tracer,
    get_tracer_provider,
    INVALID_SPAN,
    Link,
    set_span_in_context,
    TracerProvider,
)

from ._app import BackgroundJobFlaskApp
from ._defines import BackgroundJobDefines
from ._interface import BackgroundProcessInterface, JobParameters, JobTarget
from ._status import JobStatusStates
from ._store import JobStatusSpecUpdate, JobStatusStore

tracer = get_tracer()


def run_process(job_parameters: JobParameters) -> None:
    (
        stop_event,
        work_dir,
        job_id,
        target,
        lock_wato,
        is_stoppable,
        override_job_log_level,
        span_id,
        origin_span_context,
    ) = job_parameters

    logger = log.logger.getChild("background-job")
    jobstatus_store = JobStatusStore(work_dir)
    setthreadtitle(BackgroundJobDefines.process_name)

    final_status_update: JobStatusSpecUpdate = {}
    try:
        job_status = jobstatus_store.read()
        progress_update = _initialize_environment(
            logger, job_id, Path(work_dir), lock_wato, is_stoppable, override_job_log_level
        )

        with tracer.start_as_current_span(
            f"run_process[{span_id}]",
            context=set_span_in_context(INVALID_SPAN),
            attributes={
                "cmk.job_id": job_id,
                "cmk.target.callable": str(target.callable),
            },
            links=[Link(origin_span_context.to_span_context())],
        ):
            logger.log(VERBOSE, "Initialized background job (Job ID: %s)", job_id)
            jobstatus_store.update({"state": JobStatusStates.RUNNING})

            _execute_function(
                logger,
                target,
                BackgroundProcessInterface(
                    work_dir,
                    job_id,
                    logger,
                    stop_event,
                    gui_job_context_manager(job_status.user),
                    progress_update,
                ),
            )

            # Final status update
            job_status = jobstatus_store.read()

            if job_status.loginfo["JobException"]:
                final_state = JobStatusStates.EXCEPTION
            elif stop_event.is_set():
                logger.warning("Job was stopped")
                final_state = JobStatusStates.STOPPED
            else:
                final_state = JobStatusStates.FINISHED

            final_status_update = {
                "state": final_state,
                "duration": time.time() - job_status.started,
            }

    except MKTerminate:
        logger.warning("Job was stopped")
        final_status_update = {"state": JobStatusStates.STOPPED}
    except Exception:
        crash = create_gui_crash_report()
        logger.error(
            "Exception while preparing background function environment (Crash ID: %s)",
            crash.ident_to_text(),
            exc_info=True,
        )
        final_status_update = {"state": JobStatusStates.EXCEPTION}
    finally:
        # We want to be sure that all spans we created so far are flushed before the background
        # jobs goes into it's final state. There may spans come later. These are handled by an
        # atexit handler, which is registered by opentelemetry, during the finalization of the
        # interpreter, but we want to have all finished spans collected before we set the
        # background job to finished.
        if isinstance(provider := get_tracer_provider(), TracerProvider):
            provider.force_flush()

        jobstatus_store.update(final_status_update)

        # The UI code does not clean up locks properly in all cases, so we need to do it here
        # in case there were some locks left over
        store.release_all_locks()


def gui_job_context_manager(user: str | None) -> Callable[[], ContextManager[None]]:
    @contextmanager
    def gui_job_context() -> Iterator[None]:
        _load_ui()

        try:
            features = features_registry[str(edition(paths.omd_root))]
        except KeyError:
            raise ValueError(f"Invalid edition: {edition}")

        with (
            BackgroundJobFlaskApp(features).test_request_context("/"),
            SuperUserContext() if user is None else UserContext(UserId(user)),
        ):
            yield None

    return gui_job_context


def _load_ui() -> None:
    """This triggers loading all modules of the UI, internal ones and plugins"""
    # Import locally to only have it executed in the background job process and not in the launching
    # process. Moving it to the module level will significantly slow down the launching process.
    from cmk.gui import main_modules

    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


def _initialize_environment(
    logger: Logger,
    job_id: str,
    work_dir: Path,
    lock_wato: bool,
    is_stoppable: bool,
    override_job_log_level: int | None,
) -> IO[str]:
    """Setup environment (Logging, Livestatus handles, etc.)"""
    progress_update = _open_progress_update(work_dir)
    # TODO: Influences the whole process. Set level on our log handler, to have it job specific?
    _set_log_levels(override_job_log_level)
    _enable_logging_to_progress_update(progress_update)
    _lock_configuration(lock_wato)
    return progress_update


def _set_log_levels(override_job_log_level: int | None) -> None:
    log.set_log_levels(
        {
            **load_gui_log_levels(),
            **(
                {"cmk.web.background-job": override_job_log_level}
                if override_job_log_level is not None
                else {}
            ),
        }
    )


def _execute_function(
    logger: Logger,
    target: JobTarget,
    job_interface: BackgroundProcessInterface,
) -> None:
    try:
        target.callable(job_interface, target.args)
    except MKTerminate:
        raise
    except Exception as e:
        crash = create_gui_crash_report()
        logger.exception("Exception in background function (Crash ID: %s)", crash.ident_to_text())
        job_interface.send_exception(_("Exception (Crash ID: %s): %s") % (crash.ident_to_text(), e))


def _open_progress_update(work_dir: Path) -> IO[str]:
    """Set-up the job specific log file"""
    # Use buffering=1 to make each line directly visible in the job progress dialog
    return (work_dir / BackgroundJobDefines.progress_update_filename).open("w", buffering=1)


def _enable_logging_to_progress_update(progress_update: IO[str]) -> None:
    """In addition to the web.log we also want to see the job specific logs
    in stdout (which results in job progress info)"""
    handler = StreamHandler(stream=progress_update)
    handler.addFilter(ThreadLogFilter(threading.current_thread().name))
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    log.logger.addHandler(handler)


class ThreadLogFilter(logging.Filter):
    """This filter only show log entries for specified thread name"""

    def __init__(self, thread_name: str) -> None:
        super().__init__()
        self.thread_name = thread_name

    def filter(self, record: logging.LogRecord) -> bool:
        return record.threadName == self.thread_name


def _lock_configuration(lock_wato: bool) -> None:
    if lock_wato:
        store.release_all_locks()
        store.lock_exclusive(paths.configuration_lockfile)
