#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import io
import logging
import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path
from types import FrameType
from typing import Callable

from setproctitle import setthreadtitle

import cmk.utils.paths
from cmk.utils import daemon, render, store
from cmk.utils.exceptions import MKTerminate
from cmk.utils.log import VERBOSE

from cmk.gui import log, sites
from cmk.gui.i18n import _
from cmk.gui.utils.timeout_manager import timeout_manager

from ._defines import BackgroundJobDefines
from ._status import JobStatusStates
from ._store import JobStatusStore


class BackgroundProcess(multiprocessing.Process):
    """When started, BackgroundJob spawns one instance of BackgroundProcess"""

    def __init__(
        self,
        logger: logging.Logger,
        work_dir: str,
        job_id: str,
        target: Callable[[BackgroundProcessInterface], None],
    ) -> None:
        super().__init__()
        self._jobstatus_store = JobStatusStore(work_dir)
        self._logger = logger
        self._target = target
        self._job_interface = BackgroundProcessInterface(work_dir, job_id, logger)

    def _register_signal_handlers(self) -> None:
        self._logger.debug("Register signal handler %d", os.getpid())
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum: int, frame: FrameType | None) -> None:
        self._logger.debug("Received SIGTERM")
        status = self._jobstatus_store.read()
        if not status.stoppable:
            self._logger.warning(
                "Skip termination of background job (Job ID: %s, PID: %d)",
                self._job_interface.get_job_id(),
                os.getpid(),
            )
            return

        raise MKTerminate()

    def run(self) -> None:
        self._detach_from_parent()

        try:
            self.initialize_environment()
            self._logger.log(
                VERBOSE, "Initialized background job (Job ID: %s)", self._job_interface.get_job_id()
            )
            self._jobstatus_store.update(
                {
                    "pid": self.pid,
                    "state": JobStatusStates.RUNNING,
                }
            )

            # The actual function call
            self._execute_function()

            # Final status update
            job_status = self._jobstatus_store.read()

            if job_status.loginfo["JobException"]:
                final_state = JobStatusStates.EXCEPTION
            else:
                final_state = JobStatusStates.FINISHED

            self._jobstatus_store.update(
                {
                    "state": final_state,
                    "duration": time.time() - job_status.started,
                }
            )
        except MKTerminate:
            self._logger.warning("Job was stopped")
            self._jobstatus_store.update({"state": JobStatusStates.STOPPED})
        except Exception:
            self._logger.error(
                "Exception while preparing background function environment", exc_info=True
            )
            self._jobstatus_store.update({"state": JobStatusStates.EXCEPTION})

    def _detach_from_parent(self) -> None:
        # Detach from parent and cleanup inherited file descriptors
        os.setsid()

        # NOTE: Setting the thread title is not for cosmetics! BackgroundJob._is_correct_process()
        # will not do the right thing without it! Furthermore, using setproctitle() instead of
        # setthreadtitle() would be more fragile, because the former will only work if os.environ
        # has not been damaged too much, but our tests do this via mock.patch.dict(os.environ, ...).
        setthreadtitle(BackgroundJobDefines.process_name)

        sys.stdin.close()
        # NOTE
        # When forking off from an mod_wsgi process, these handles are not the standard stdout and
        # stderr handles but rather proxies to internal data-structures of mod_wsgi. If these are
        # closed then mod_wsgi will trigger a "RuntimeError: log object has expired" if you want to
        # use them again, as this is considered a programming error. The logging framework
        # installs an "atexit" callback which flushes the logs upon the process exiting. This
        # tries to write to the now closed fake stdout/err handles and triggers the RuntimeError.
        # This will happen even if sys.stdout and sys.stderr are reset to their originals because
        # the logging.StreamHandler will still hold a reference to the mod_wsgi stdout/err handles.
        # sys.stdout.close()
        # sys.stderr.close()
        daemon.closefrom(0)

    def initialize_environment(self) -> None:
        """Setup environment (Logging, Livestatus handles, etc.)"""
        self._init_gui_logging()
        self._disable_timeout_manager()
        self._cleanup_livestatus_connections()
        self._open_stdout_and_stderr()
        self._enable_logging_to_stdout()
        self._register_signal_handlers()
        self._lock_configuration()

    def _init_gui_logging(self) -> None:
        log.init_logging()  # NOTE: We run in a subprocess!
        self._logger = log.logger.getChild("background-job")
        self._log_path_hint = _("More information can be found in ~/var/log/web.log")

    def _disable_timeout_manager(self) -> None:
        if timeout_manager:
            timeout_manager.disable_timeout()

    def _cleanup_livestatus_connections(self) -> None:
        """Close livestatus connections inherited from the parent process"""
        sites.disconnect()

    def _execute_function(self) -> None:
        try:
            self._target(self._job_interface)
        except MKTerminate:
            raise
        except Exception as e:
            self._logger.exception("Exception in background function")
            self._job_interface.send_exception(_("Exception: %s") % (e))

    def _open_stdout_and_stderr(self) -> None:
        """Create a temporary file and use it as stdout / stderr buffer"""
        # - We can not use io.BytesIO() or similar because we need real file descriptors
        #   to be able to catch the (debug) output of libraries like libldap or subproccesses
        # - Use buffering=0 to make the non flushed output directly visible in
        #   the job progress dialog
        # - Python 3's stdout and stderr expect 'str' not 'bytes'
        unbuffered = (
            Path(self._job_interface.get_work_dir()) / BackgroundJobDefines.progress_update_filename
        ).open("wb", buffering=0)
        sys.stdout = sys.stderr = io.TextIOWrapper(unbuffered, write_through=True)
        os.dup2(sys.stdout.fileno(), 1)
        os.dup2(sys.stderr.fileno(), 2)

    def _enable_logging_to_stdout(self) -> None:
        """In addition to the web.log we also want to see the job specific logs
        in stdout (which results in job progress info)"""
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(cmk.utils.log.get_formatter())
        log.logger.addHandler(handler)

    def _lock_configuration(self) -> None:
        if self._jobstatus_store.read().lock_wato:
            store.release_all_locks()
            store.lock_exclusive()


class BackgroundProcessInterface:
    def __init__(self, work_dir: str, job_id: str, logger: logging.Logger) -> None:
        self._work_dir = work_dir
        self._job_id = job_id
        self._logger = logger

    def get_work_dir(self) -> str:
        return self._work_dir

    def get_job_id(self) -> str:
        return self._job_id

    def get_logger(self) -> logging.Logger:
        return self._logger

    def send_progress_update(self, info: str, with_timestamp: bool = False) -> None:
        """The progress update is written to stdout and will be caught by the threads counterpart"""
        message = info
        if with_timestamp:
            message = f"{render.time_of_day(time.time())} {message}"
        sys.stdout.write(message + "\n")

    def send_result_message(self, info: str) -> None:
        """The result message is written to a distinct file to separate this info from the rest of
        the context information. This message should contain a short result message and/or some kind
        of resulting data, e.g. a link to a report or an agent output. As it may contain HTML code
        it is not written to stdout."""
        encoded_info = "%s\n" % info
        result_message_path = (
            Path(self.get_work_dir()) / BackgroundJobDefines.result_message_filename
        )
        with result_message_path.open("ab") as f:
            f.write(encoded_info.encode())

    def send_exception(self, info: str) -> None:
        """Exceptions are written to stdout because of log output clarity
        as well as into a distinct file, to separate this info from the rest of the context information
        """
        # Exceptions also get an extra newline, since some error messages tend not output a \n at the end..
        encoded_info = "%s\n" % info
        sys.stdout.write(encoded_info)
        with (Path(self.get_work_dir()) / BackgroundJobDefines.exceptions_filename).open("ab") as f:
            f.write(encoded_info.encode())
