#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import os
import shutil
import signal
import time
from typing import Callable, NoReturn, TypedDict

import psutil

from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.regex import regex, REGEX_GENERIC_IDENTIFIER
from cmk.utils.user import UserId

from cmk.gui import log
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.urls import makeuri_contextless

from ._defines import BackgroundJobDefines
from ._process import BackgroundProcess, BackgroundProcessInterface
from ._status import BackgroundStatusSnapshot, InitialStatusArgs, JobStatusSpec, JobStatusStates
from ._store import JobStatusStore


class BackgroundJobAlreadyRunning(MKGeneralException):
    pass


class JobParameters(TypedDict):
    """Just a small wrapper to help improve the typing through multiprocessing.Process call"""

    work_dir: str
    job_id: str
    target: Callable[[BackgroundProcessInterface], None]


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
