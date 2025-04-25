#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Background job process entry point.

This must not be imported from anywhere outside of the background job process."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager as ContextManager
from contextlib import contextmanager, nullcontext
from logging import Formatter, Logger, StreamHandler
from pathlib import Path
from typing import IO, override

from setproctitle import setthreadtitle

from cmk.ccc import store
from cmk.ccc.exceptions import MKTerminate, MKTimeout
from cmk.ccc.user import UserId
from cmk.ccc.version import edition

from cmk.utils import paths
from cmk.utils.log import VERBOSE

from cmk.gui import log
from cmk.gui.crash_handler import create_gui_crash_report
from cmk.gui.features import features_registry
from cmk.gui.i18n import _
from cmk.gui.session import SuperUserContext, UserContext
from cmk.gui.single_global_setting import load_gui_log_levels

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
        # TODO: Influences the whole process. Set level on our log handler, to have it job specific?
        _set_log_levels(override_job_log_level)

        with (
            _open_progress_update(Path(work_dir)) as progress_update,
            _progress_update_logging(progress_update),
            tracer.span(
                f"run_process[{span_id}]",
                context=set_span_in_context(INVALID_SPAN),
                attributes={
                    "cmk.job_id": job_id,
                    "cmk.target.callable": str(target.callable),
                },
                links=[Link(origin_span_context.to_span_context())],
            ),
            (
                store.lock_checkmk_configuration(paths.configuration_lockfile)
                if lock_wato
                else nullcontext()
            ),
        ):
            logger.log(VERBOSE, "Initialized background job (Job ID: %s)", job_id)
            jobstatus_store.update(
                {
                    "state": JobStatusStates.RUNNING,
                    "ppid": os.getpid(),
                    "pid": threading.get_native_id(),
                }
            )

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
    except MKTimeout:
        logger.warning("Job stopped due to timeout")
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


def _execute_function(
    logger: Logger,
    target: JobTarget,
    job_interface: BackgroundProcessInterface,
) -> None:
    try:
        target.callable(job_interface, target.args)
    except MKTerminate:
        raise
    except MKTimeout:
        raise
    except Exception as e:
        crash = create_gui_crash_report()
        logger.exception("Exception in background function (Crash ID: %s)", crash.ident_to_text())
        job_interface.send_exception(_("Exception (Crash ID: %s): %s") % (crash.ident_to_text(), e))


def _open_progress_update(work_dir: Path) -> IO[str]:
    """Set-up the job specific log file"""
    # Use buffering=1 to make each line directly visible in the job progress dialog
    return (work_dir / BackgroundJobDefines.progress_update_filename).open("w", buffering=1)


@contextmanager
def _progress_update_logging(progress_update: IO[str]) -> Iterator[None]:
    log.logger.addHandler(progress_update_handler := _progress_update_handler(progress_update))
    try:
        yield
    finally:
        log.logger.removeHandler(progress_update_handler)


def _progress_update_handler(progress_update: IO[str]) -> StreamHandler:
    """In addition to the web.log we also want to see the job specific logs
    in stdout (which results in job progress info)"""
    handler = StreamHandler(stream=progress_update)
    handler.addFilter(ThreadLogFilter(threading.current_thread().name))
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    return handler


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


class ThreadLogFilter(logging.Filter):
    """This filter only show log entries for specified thread name"""

    def __init__(self, thread_name: str) -> None:
        super().__init__()
        self.thread_name = thread_name

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return record.threadName == self.thread_name
