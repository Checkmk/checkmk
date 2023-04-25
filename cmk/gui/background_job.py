#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import io
import logging
import multiprocessing
import os
import shutil
import signal
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, NoReturn, TypedDict

import psutil
from pydantic import BaseModel
from setproctitle import setthreadtitle

import cmk.utils.daemon as daemon
import cmk.utils.log
import cmk.utils.plugin_registry
import cmk.utils.render as render
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException, MKTerminate
from cmk.utils.log import VERBOSE
from cmk.utils.regex import regex, REGEX_GENERIC_IDENTIFIER
from cmk.utils.type_defs import UserId

from cmk.gui import log, sites
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.timeout_manager import timeout_manager
from cmk.gui.utils.urls import makeuri_contextless

JobId = str


class JobParameters(TypedDict):
    """Just a small wrapper to help improve the typing through multiprocessing.Process call"""

    work_dir: str
    job_id: str
    target: Callable[[BackgroundProcessInterface], None]


class JobStatusStates:
    INITIALIZED = "initialized"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    EXCEPTION = "exception"


@dataclass
class InitialStatusArgs:
    title: str = "Background job"
    stoppable: bool = True
    deletable: bool = True
    user: str | None = None
    estimated_duration: float | None = None
    logfile_path: str = ""
    lock_wato: bool = False
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str = ""


class JobLogInfo(TypedDict):
    JobProgressUpdate: Sequence[str]
    JobResult: Sequence[str]
    JobException: Sequence[str]


class JobStatusSpec(BaseModel):
    state: str  # Make Literal["initialized", "running", "finished", "stopped", "exception"]
    started: float  # Change to Timestamp type later
    pid: int | None
    loginfo: JobLogInfo
    is_active: bool  # Remove this field and always derive from state dynamically?
    duration: float = 0.0
    title: str = "Background job"
    stoppable: bool = True
    deletable: bool = True
    user: str | None = None
    estimated_duration: float | None = None
    ppid: int | None = None
    logfile_path: str = ""  # Move out of job status -> Has a static value
    acknowledged_by: str | None = None
    lock_wato: bool = False
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str = ""


# Same as JobStatusSpec but without mandatory attributes. Is there a way to prevent the duplication?
class JobStatusSpecUpdate(TypedDict, total=False):
    state: str  # Make Literal["initialized", "running", "finished", "stopped", "exception"]
    started: float  # Change to Timestamp type later
    pid: int | None
    loginfo: JobLogInfo
    is_active: bool
    duration: float  # Make this mandatory
    title: str
    stoppable: bool
    deletable: bool
    user: str | None
    estimated_duration: float | None
    ppid: int
    logfile_path: str
    acknowledged_by: str | None
    lock_wato: bool
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str


@dataclass
class BackgroundStatusSnapshot:
    job_id: JobId
    status: JobStatusSpec
    exists: bool
    is_active: bool
    has_exception: bool
    acknowledged_by: str | None
    may_stop: bool
    may_delete: bool


class BackgroundJobAlreadyRunning(MKGeneralException):
    pass


# .
#   .--Function Interface--------------------------------------------------.
#   |               _____                 _   _                            |
#   |              |  ___|   _ _ __   ___| |_(_) ___  _ __                 |
#   |              | |_ | | | | '_ \ / __| __| |/ _ \| '_ \                |
#   |              |  _|| |_| | | | | (__| |_| | (_) | | | |               |
#   |              |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|               |
#   |                                                                      |
#   |              ___       _             __                              |
#   |             |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___               |
#   |              | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \              |
#   |              | || | | | ||  __/ |  |  _| (_| | (_|  __/              |
#   |             |___|_| |_|\__\___|_|  |_|  \__,_|\___\___|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


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
        """The progress update is written to stdout and will be catched by the threads counterpart"""
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


# .
#   .--Background Process--------------------------------------------------.
#   |       ____             _                                   _         |
#   |      | __ )  __ _  ___| | ____ _ _ __ ___  _   _ _ __   __| |        |
#   |      |  _ \ / _` |/ __| |/ / _` | '__/ _ \| | | | '_ \ / _` |        |
#   |      | |_) | (_| | (__|   < (_| | | | (_) | |_| | | | | (_| |        |
#   |      |____/ \__,_|\___|_|\_\__, |_|  \___/ \__,_|_| |_|\__,_|        |
#   |                            |___/                                     |
#   |                  ____                                                |
#   |                 |  _ \ _ __ ___   ___ ___  ___ ___                   |
#   |                 | |_) | '__/ _ \ / __/ _ \/ __/ __|                  |
#   |                 |  __/| | | (_) | (_|  __/\__ \__ \                  |
#   |                 |_|   |_|  \___/ \___\___||___/___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | When started, BackgroundJob spawns one instance of BackgroundProcess |
#   '----------------------------------------------------------------------'


class BackgroundProcess(multiprocessing.Process):
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


class BackgroundJobDefines:
    base_dir = os.path.join(cmk.utils.paths.var_dir, "background_jobs")
    process_name = (
        "cmk-job"  # NOTE: keep this name short! psutil.Process tends to truncate long names
    )

    jobstatus_filename = "jobstatus.mk"
    progress_update_filename = "progress_update"
    exceptions_filename = "exceptions"
    result_message_filename = "result_message"


# .
#   .--Background Job------------------------------------------------------.
#   |       ____             _                                   _         |
#   |      | __ )  __ _  ___| | ____ _ _ __ ___  _   _ _ __   __| |        |
#   |      |  _ \ / _` |/ __| |/ / _` | '__/ _ \| | | | '_ \ / _` |        |
#   |      | |_) | (_| | (__|   < (_| | | | (_) | |_| | | | | (_| |        |
#   |      |____/ \__,_|\___|_|\_\__, |_|  \___/ \__,_|_| |_|\__,_|        |
#   |                            |___/                                     |
#   |                              _       _                               |
#   |                             | | ___ | |__                            |
#   |                          _  | |/ _ \| '_ \                           |
#   |                         | |_| | (_) | |_) |                          |
#   |                          \___/ \___/|_.__/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class BackgroundJob:
    housekeeping_max_age_sec = 86400 * 30
    housekeeping_max_count = 50

    # TODO: Make this an abstract property
    job_prefix = "unnamed-job"

    @classmethod
    def gui_title(cls) -> str:
        # FIXME: This method cannot be made abstract since GUIBackgroundJob is
        # instantiated in various places.
        raise NotImplementedError()

    def __init__(
        self,
        job_id: str,
        initial_status_args: InitialStatusArgs | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__()
        self.validate_job_id(job_id)
        self._job_id = job_id
        self._job_base_dir = BackgroundJobDefines.base_dir
        self._job_initializiation_lock = os.path.join(self._job_base_dir, "job_initialization.lock")

        self._logger = logger if logger else log.logger.getChild("background-job")

        if initial_status_args is None:
            initial_status_args = InitialStatusArgs()
        initial_status_args.user = str(user.id) if user.id else None
        initial_status_args.logfile_path = "~/var/log/web.log"
        self._initial_status_args = initial_status_args

        self._work_dir = os.path.join(self._job_base_dir, self._job_id)
        self._jobstatus_store = JobStatusStore(self._work_dir)

    @staticmethod
    def validate_job_id(job_id: str) -> None:
        if not regex(REGEX_GENERIC_IDENTIFIER).match(job_id):
            raise MKGeneralException(_("Invalid Job ID"))

    def get_job_id(self) -> str:
        return self._job_id

    def get_title(self) -> str:
        return self._jobstatus_store.read().title

    def get_work_dir(self) -> str:
        return self._work_dir

    def exists(self) -> bool:
        return os.path.exists(self._work_dir) and self._jobstatus_store.exists()

    def is_available(self) -> bool:
        return self.exists() and self.is_visible()

    def is_deletable(self) -> bool:
        return self.get_status().deletable

    def is_stoppable(self) -> bool:
        return self._jobstatus_store.read().stoppable

    def is_visible(self) -> bool:
        if user.may("background_jobs.see_foreign_jobs"):
            return True
        return user.id == self.get_status().user

    def may_stop(self) -> bool:
        if not self.is_stoppable():
            return False

        if not user.may("background_jobs.stop_jobs"):
            return False

        if self._is_foreign() and not user.may("background_jobs.stop_foreign_jobs"):
            return False

        if not self.is_active():
            return False

        return True

    def may_delete(self) -> bool:
        if not self.is_deletable():
            return False

        if not self.is_stoppable() and self.is_active():
            return False

        if not user.may("background_jobs.delete_jobs"):
            return False

        if self._is_foreign() and not user.may("background_jobs.delete_foreign_jobs"):
            return False

        return True

    def _is_foreign(self) -> bool:
        return self.get_status().user != user.id

    def _verify_running(self, job_status: JobStatusSpec) -> bool:
        if job_status.state == JobStatusStates.INITIALIZED:
            # The process was created a millisecond ago
            # The child process however, did not have time to update the statefile with its PID
            # We consider this scenario as OK, if the start time was recent enough
            if time.time() - job_status.started < 5:  # 5 seconds
                return True

        if job_status.pid is None:
            return False

        try:
            p = psutil.Process(job_status.pid)
            if self._is_correct_process(job_status, p):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

        return False

    def is_active(self) -> bool:
        if not self.exists():
            return False

        job_status = self.get_status()
        return job_status.is_active and self._verify_running(job_status)

    def stop(self) -> None:
        if not self.is_active():
            raise MKGeneralException(_("Job already finished"))

        if not self.is_stoppable():
            raise MKGeneralException(_("This job cannot be stopped"))

        self._terminate_processes()

        job_status = self._jobstatus_store.read()
        duration = time.time() - job_status.started
        self._jobstatus_store.update(
            {
                "state": JobStatusStates.STOPPED,
                "duration": duration,
            }
        )

    def delete(self) -> None:
        if not self.is_stoppable() and self.is_active():
            raise MKGeneralException(_("Cannot delete job. Job cannot be stopped."))

        self._terminate_processes()
        self._delete_work_dir()

    def _delete_work_dir(self) -> None:
        try:
            # In SUP-10240 we encountered a crash in the following line with the reason
            # "Directory not empty" while setting up the "search_index" background job.
            # The shutil.rmtree call recursively removes all the files/folders under the folder tree
            # so the error seems to be caused by another process adding a file/folder under that
            # tree while the shutil.rmtree call is executing.
            # We didn't manage to reproduce the issue with the code and it seems to be really rare.
            # More details in SUP-10240
            shutil.rmtree(self._work_dir)
        except FileNotFoundError:
            pass

    def _terminate_processes(self) -> None:
        job_status = self.get_status()

        if job_status.pid is None:
            return

        # Send SIGTERM
        self._logger.debug(
            'Stopping job using SIGTERM "%s" (PID: %s)', self._job_id, job_status.pid
        )
        try:
            process = psutil.Process(job_status.pid)
            if not self._is_correct_process(job_status, process):
                return
            process.send_signal(signal.SIGTERM)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        self._logger.debug("Waiting for job")
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 seconds SIGTERM grace period
            job_still_running = False
            try:
                process = psutil.Process(job_status.pid)
                if not self._is_correct_process(job_status, process):
                    return
                job_still_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

            if not job_still_running:
                break
            time.sleep(0.1)

        try:
            p = psutil.Process(job_status.pid)
            if self._is_correct_process(job_status, process):
                # Kill unresponsive jobs
                self._logger.debug("Killing job")
                p.send_signal(signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

    def _is_correct_process(
        self, job_status: JobStatusSpec, psutil_process: psutil.Process
    ) -> bool:
        if psutil_process.name() != BackgroundJobDefines.process_name:
            return False

        return True

    def get_status(self) -> JobStatusSpec:
        status = self._jobstatus_store.read()

        # Some dynamic stuff
        if status.state == JobStatusStates.RUNNING and status.pid is not None:
            try:
                p = psutil.Process(status.pid)
                if not self._is_correct_process(status, p):
                    status.state = JobStatusStates.STOPPED
                else:
                    status.duration = time.time() - status.started
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                status.state = JobStatusStates.STOPPED

        map_job_state_to_is_active = {
            JobStatusStates.INITIALIZED: True,
            JobStatusStates.RUNNING: True,
            JobStatusStates.FINISHED: False,
            JobStatusStates.STOPPED: False,
            JobStatusStates.EXCEPTION: False,
        }
        status.is_active = map_job_state_to_is_active[status.state]

        return status

    def start(self, target: Callable[[BackgroundProcessInterface], None]) -> None:
        with store.locked(self._job_initializiation_lock):
            self._start(target)

    def _start(self, target: Callable[[BackgroundProcessInterface], None]) -> None:
        if self.is_active():
            raise BackgroundJobAlreadyRunning(_("Background Job %s already running") % self._job_id)

        self._prepare_work_dir()

        # Start processes
        initial_status = JobStatusSpec(
            state=JobStatusStates.INITIALIZED,
            started=time.time(),
            duration=0.0,
            pid=None,
            is_active=False,
            loginfo={
                "JobProgressUpdate": [],
                "JobResult": [],
                "JobException": [],
            },
            title=self._initial_status_args.title,
            stoppable=self._initial_status_args.stoppable,
            deletable=self._initial_status_args.deletable,
            user=self._initial_status_args.user,
            estimated_duration=self._initial_status_args.estimated_duration,
            logfile_path=self._initial_status_args.logfile_path,
            lock_wato=self._initial_status_args.lock_wato,
            host_name=self._initial_status_args.host_name,
        )
        self._jobstatus_store.write(initial_status)

        job_parameters = JobParameters(
            {
                "work_dir": self._work_dir,
                "job_id": self._job_id,
                "target": target,
            }
        )
        p = multiprocessing.Process(
            target=self._start_background_subprocess, args=(job_parameters,)
        )

        p.start()
        p.join()

        if p.exitcode == 0:
            job_status = self.get_status()
            self._logger.debug('Started job "%s" (PID: %s)', self._job_id, job_status.pid)

    def _prepare_work_dir(self) -> None:
        self._delete_work_dir()
        os.makedirs(self._work_dir)

    def _start_background_subprocess(self, job_parameters: JobParameters) -> None:
        try:
            # Even the "short living" intermediate process here needs to close
            # the inherited file descriptors as soon as possible to prevent
            # race conditions with inherited locks that have been inherited
            # from the parent process. The job_initialization.lock is such a
            # thing we had a problem with when background jobs were initialized
            # while the apache tried to stop / restart.
            #
            # Had problems with closefrom() during the tests. Explicitly
            # closing the locks here instead of closing all fds to keep logging
            # related fds open.
            # daemon.closefrom(3)
            store.release_all_locks()

            self._jobstatus_store.update({"ppid": os.getpid()})

            p = BackgroundProcess(
                logger=log.logger.getChild("background_process"),
                work_dir=job_parameters["work_dir"],
                job_id=job_parameters["job_id"],
                target=job_parameters["target"],
            )
            p.start()
        except Exception as e:
            self._logger.exception("Error while starting subprocess: %s", e)
            self._exit(1)
        self._exit(0)

    def _exit(self, code: int) -> NoReturn:
        """Exit the interpreter.

        This is here so we can mock this away cleanly."""
        os._exit(code)

    def wait_for_completion(self) -> None:
        """Wait for background job to be complete."""
        while self.is_active():
            time.sleep(0.5)

    def get_status_snapshot(self) -> BackgroundStatusSnapshot:
        status = self.get_status()
        return BackgroundStatusSnapshot(
            job_id=self.get_job_id(),
            status=status,
            exists=self.exists(),
            is_active=self.is_active(),
            has_exception=status.state == JobStatusStates.EXCEPTION,
            acknowledged_by=status.acknowledged_by,
            may_stop=self.may_stop(),
            may_delete=self.may_delete(),
        )

    def acknowledge(self, user_id: UserId | None) -> None:
        self._jobstatus_store.update({"acknowledged_by": str(user.id) if user.id else None})

    def detail_url(self) -> str:
        """Returns the URL that displays the job detail page"""
        return makeuri_contextless(
            request,
            [
                ("mode", "background_job_details"),
                ("job_id", self.get_job_id()),
                ("back_url", self._back_url()),
            ],
            filename="wato.py",
        )

    def _back_url(self) -> str | None:
        """Returns either None or the URL that the job detail page may be link back"""
        return None


class BackgroundJobRegistry(cmk.utils.plugin_registry.Registry[type[BackgroundJob]]):
    def plugin_name(self, instance: type[BackgroundJob]) -> str:
        return instance.__name__


job_registry = BackgroundJobRegistry()


class JobStatusStore:
    def __init__(self, work_dir: str) -> None:
        super().__init__()
        self._work_dir = work_dir
        self._jobstatus_path = Path(work_dir) / BackgroundJobDefines.jobstatus_filename

        self._progress_update_path = Path(work_dir) / BackgroundJobDefines.progress_update_filename
        self._result_message_path = Path(work_dir) / BackgroundJobDefines.result_message_filename
        self._exceptions_path = Path(work_dir) / BackgroundJobDefines.exceptions_filename

    def read(self) -> JobStatusSpec:
        initialized = JobStatusSpec(
            state=JobStatusStates.INITIALIZED,
            started=time.time(),
            pid=None,
            is_active=False,
            loginfo={
                "JobProgressUpdate": [
                    _(
                        "Waiting for first status update from the job. In case "
                        "this message is shown for a longer time, the startup "
                        "got interrupted."
                    )
                ],
                "JobResult": [],
                "JobException": [],
            },
        )

        if not self._jobstatus_path.exists():
            return initialized

        initialized.started = self._jobstatus_path.stat().st_mtime

        if not (raw_status_spec := self.read_raw()):
            # Job status file might have just been created during locking. In this
            # case the file does not have any content yet and falls back to the default
            # value, which is an empty dict.
            return initialized

        try:
            data: JobStatusSpec = JobStatusSpec.parse_obj(raw_status_spec)
        finally:
            store.release_lock(str(self._jobstatus_path))

        def _log_lines(path: Path) -> list[str]:
            try:
                with path.open(encoding="utf-8") as f:
                    return f.read().splitlines()
            except FileNotFoundError:
                return []

        data.loginfo["JobProgressUpdate"] = _log_lines(self._progress_update_path)
        data.loginfo["JobResult"] = _log_lines(self._result_message_path)
        data.loginfo["JobException"] = _log_lines(self._exceptions_path)

        return data

    def read_raw(self) -> dict[str, Any]:
        status: dict[str, Any] = store.load_object_from_file(
            self._jobstatus_path, default={}, lock=True
        )
        return status

    def exists(self) -> bool:
        return self._jobstatus_path.exists()

    def write(self, status: JobStatusSpec) -> None:
        store.save_object_to_file(self._jobstatus_path, status.dict())

    def update(self, params: JobStatusSpecUpdate) -> None:
        if not self._jobstatus_path.parent.exists():
            return

        if params:
            try:
                self.write(JobStatusSpec.parse_obj({**self.read_raw(), **params}))
            finally:
                store.release_lock(str(self._jobstatus_path))


class BackgroundJobManager:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger.getChild("job_manager")
        super().__init__()

    def get_running_job_ids(self, job_class: type[BackgroundJob]) -> list[JobId]:
        """Checks for running jobs in the jobs default basedir"""
        all_jobs = self.get_all_job_ids(job_class)
        return [
            job_id for job_id in all_jobs if BackgroundJob(job_id, logger=self._logger).is_active()
        ]

    def get_all_job_ids(self, job_class: type[BackgroundJob]) -> list[JobId]:
        """Checks for running jobs in the jobs default basedir"""
        job_ids: list[JobId] = []
        if not os.path.exists(BackgroundJobDefines.base_dir):
            return job_ids

        for dirname in sorted(os.listdir(BackgroundJobDefines.base_dir)):
            if not dirname.startswith(job_class.job_prefix):
                continue
            job_ids.append(dirname)

        return job_ids

    def do_housekeeping(self, job_classes: Sequence[type[BackgroundJob]]) -> None:
        try:
            for job_class in job_classes:
                job_ids = self.get_all_job_ids(job_class)
                max_age = job_class.housekeeping_max_age_sec
                max_count = job_class.housekeeping_max_count
                all_jobs: list[tuple[str, JobStatusSpec]] = []

                job_instances = {}
                for job_id in job_ids:
                    job_instances[job_id] = BackgroundJob(job_id, logger=self._logger)
                    all_jobs.append((job_id, job_instances[job_id].get_status()))
                all_jobs.sort(key=lambda x: x[1].started, reverse=True)

                for entry in all_jobs[-1:0:-1]:
                    job_id, job_status = entry
                    if job_status.state == JobStatusStates.RUNNING:
                        continue

                    if len(all_jobs) > max_count or (time.time() - job_status.started > max_age):
                        job_instances[job_id].delete()
                        all_jobs.remove(entry)
        except Exception:
            self._logger.error(traceback.format_exc())


def execute_housekeeping_job() -> None:
    housekeep_classes = list(job_registry.values())
    BackgroundJobManager(log.logger).do_housekeeping(housekeep_classes)
