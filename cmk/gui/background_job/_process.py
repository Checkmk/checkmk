#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Background job process entry point.

This must not be imported from anywhere outside of the background job process."""

from __future__ import annotations

import io
import os
import signal
import sys
import time
from collections.abc import Callable
from functools import partial
from logging import Formatter, Logger, StreamHandler
from pathlib import Path
from types import FrameType

from setproctitle import setthreadtitle

from cmk.utils import store
from cmk.utils.exceptions import MKTerminate
from cmk.utils.log import VERBOSE
from cmk.utils.paths import configuration_lockfile

from cmk.gui import config, log, main_modules
from cmk.gui.i18n import _
from cmk.gui.utils import get_failed_plugins

from ._app import BackgroundJobFlaskApp
from ._defines import BackgroundJobDefines
from ._interface import BackgroundProcessInterface
from ._status import JobStatusStates
from ._store import JobStatusStore


def run_process(
    work_dir: str,
    job_id: str,
    target: Callable[[BackgroundProcessInterface], None],
    lock_wato: bool,
    is_stoppable: bool,
    override_job_log_level: int | None = None,
) -> None:
    logger = log.logger.getChild("background-job")
    jobstatus_store = JobStatusStore(work_dir)
    _detach_from_parent()

    try:
        with BackgroundJobFlaskApp().test_request_context("/"):
            job_status = jobstatus_store.read()
            _initialize_environment(
                logger, job_id, Path(work_dir), lock_wato, is_stoppable, override_job_log_level
            )
            logger.log(VERBOSE, "Initialized background job (Job ID: %s)", job_id)
            jobstatus_store.update({"pid": os.getpid(), "state": JobStatusStates.RUNNING})

            _execute_function(logger, target, BackgroundProcessInterface(work_dir, job_id, logger))

        # Final status update
        job_status = jobstatus_store.read()

        if job_status.loginfo["JobException"]:
            final_state = JobStatusStates.EXCEPTION
        else:
            final_state = JobStatusStates.FINISHED

        jobstatus_store.update(
            {
                "state": final_state,
                "duration": time.time() - job_status.started,
            }
        )
    except MKTerminate:
        logger.warning("Job was stopped")
        jobstatus_store.update({"state": JobStatusStates.STOPPED})
    except Exception:
        logger.error("Exception while preparing background function environment", exc_info=True)
        jobstatus_store.update({"state": JobStatusStates.EXCEPTION})


def _load_ui() -> None:
    """This triggers loading all modules of the UI, internal ones and plugins"""
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


def _register_signal_handlers(logger: Logger, is_stoppable: bool, job_id: str) -> None:
    logger.debug("Register signal handler %d", os.getpid())
    signal.signal(signal.SIGTERM, partial(_handle_sigterm, logger, is_stoppable, job_id))


def _handle_sigterm(
    logger: Logger, is_stoppable: bool, job_id: str, signum: int, frame: FrameType | None
) -> None:
    logger.debug("Received SIGTERM")
    if not is_stoppable:
        logger.warning(
            "Skip termination of background job (Job ID: %s, PID: %d)",
            job_id,
            os.getpid(),
        )
        return

    raise MKTerminate()


def _detach_from_parent() -> None:
    # Detach from parent
    os.setsid()

    # NOTE: Setting the thread title is not for cosmetics! BackgroundJob._is_correct_process()
    # will not do the right thing without it! Furthermore, using setproctitle() instead of
    # setthreadtitle() would be more fragile, because the former will only work if os.environ
    # has not been damaged too much, but our tests do this via mock.patch.dict(os.environ, ...).
    setthreadtitle(BackgroundJobDefines.process_name)


def _initialize_environment(
    logger: Logger,
    job_id: str,
    work_dir: Path,
    lock_wato: bool,
    is_stoppable: bool,
    override_job_log_level: int | None,
) -> None:
    """Setup environment (Logging, Livestatus handles, etc.)"""
    _open_stdout_and_stderr(work_dir)
    config.initialize()
    _enable_logging_to_stdout()
    _init_job_logging(logger, override_job_log_level)
    _load_ui()
    _register_signal_handlers(logger, is_stoppable, job_id)
    _lock_configuration(lock_wato)


def _init_job_logging(logger: Logger, override_job_log_level: int | None) -> None:
    if override_job_log_level:
        logger.setLevel(override_job_log_level)


def _execute_function(
    logger: Logger,
    target: Callable[[BackgroundProcessInterface], None],
    job_interface: BackgroundProcessInterface,
) -> None:
    try:
        target(job_interface)
    except MKTerminate:
        raise
    except Exception as e:
        logger.exception("Exception in background function")
        job_interface.send_exception(_("Exception: %s") % (e))


def _open_stdout_and_stderr(work_dir: Path) -> None:
    """Create a temporary file and use it as stdout / stderr buffer"""
    # - We can not use io.BytesIO() or similar because we need real file descriptors
    #   to be able to catch the (debug) output of libraries like libldap or subproccesses
    # - Use buffering=0 to make the non flushed output directly visible in
    #   the job progress dialog
    # - Python 3's stdout and stderr expect 'str' not 'bytes'
    unbuffered = (work_dir / BackgroundJobDefines.progress_update_filename).open("wb", buffering=0)
    sys.stdout = sys.stderr = io.TextIOWrapper(unbuffered, write_through=True)
    os.dup2(sys.stdout.fileno(), 1)
    os.dup2(sys.stderr.fileno(), 2)


def _enable_logging_to_stdout() -> None:
    """In addition to the web.log we also want to see the job specific logs
    in stdout (which results in job progress info)"""
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    log.logger.addHandler(handler)


def _lock_configuration(lock_wato: bool) -> None:
    if lock_wato:
        store.release_all_locks()
        store.lock_exclusive(configuration_lockfile)
