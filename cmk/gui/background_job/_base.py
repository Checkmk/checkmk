#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import shutil
import time

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.utils.regex import regex, REGEX_GENERIC_IDENTIFIER

from cmk.gui import log
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.job_scheduler_client import StartupError
from cmk.gui.logged_in import user
from cmk.gui.utils.urls import makeuri_contextless

from cmk.trace import get_tracer, SpanContext, Status, StatusCode

from ._defines import BackgroundJobDefines
from ._executor import AlreadyRunningError, JobExecutor, ThreadedJobExecutor
from ._interface import JobTarget, SpanContextModel
from ._job_scheduler_executor import JobSchedulerExecutor
from ._status import BackgroundStatusSnapshot, InitialStatusArgs, JobStatusSpec, JobStatusStates
from ._store import JobStatusStore

tracer = get_tracer()


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

    @classmethod
    def on_scheduler_start(cls, executor: JobExecutor, *, debug: bool) -> None:
        """Called when the job scheduler starts

        Can be used to implement initialization tasks that should be triggered once
        the job scheduler is ready to start background jobs"""

    def __init__(
        self,
        job_id: str,
        logger: logging.Logger | None = None,
        executor: JobExecutor | None = None,
    ) -> None:
        super().__init__()
        self.validate_job_id(job_id)
        self._job_id = job_id
        self._job_base_dir = BackgroundJobDefines.base_dir

        self._logger = logger if logger else log.logger.getChild("background-job")

        self._work_dir = os.path.join(self._job_base_dir, self._job_id)
        self._jobstatus_store = JobStatusStore(self._work_dir)

        self._executor: JobExecutor = (
            executor
            if executor
            else (
                ThreadedJobExecutor(self._logger)
                if os.environ.get("_CMK_BG_JOBS_WITHOUT_JOB_SCHEDULER") == "1"
                else JobSchedulerExecutor(self._logger)
            )
        )

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

    def is_active(self) -> bool:
        result = self._executor.is_alive(self._job_id)
        if result.is_error():
            return False
        return result.ok

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
        if (result := self._executor.terminate(self._job_id)).is_error():
            raise MKGeneralException(_("Failed to stop job: %s") % result.error)

    def get_status(self) -> JobStatusSpec:
        status = self._jobstatus_store.read()

        # Some dynamic stuff
        if status.state == JobStatusStates.RUNNING:
            status.duration = time.time() - status.started

        map_job_state_to_is_active = {
            JobStatusStates.INITIALIZED: True,
            JobStatusStates.RUNNING: True,
            JobStatusStates.FINISHED: False,
            JobStatusStates.STOPPED: False,
            JobStatusStates.EXCEPTION: False,
        }
        status.is_active = map_job_state_to_is_active[status.state]

        return status

    def start(
        self,
        target: JobTarget,
        initial_status_args: InitialStatusArgs,
        override_job_log_level: int | None = None,
    ) -> result.Result[None, AlreadyRunningError | StartupError]:
        with tracer.span(f"start_background_job[{self._job_id}]") as span:
            if (
                start_result := self._start(
                    target,
                    initial_status_args,
                    override_job_log_level,
                    span.get_span_context(),
                )
            ).is_ok():
                self._logger.debug('Started job "%s"', self._job_id)
            else:
                self._logger.debug('Failed to start job "%s"', self._job_id)
                if not isinstance(start_result.error, AlreadyRunningError):
                    # Callers decided on the severity of this case, so we don't report this as an
                    # error condition here.
                    span.set_status(Status(StatusCode.ERROR, str(start_result.error)))
            return start_result

    def _start(
        self,
        target: JobTarget,
        initial_status_args: InitialStatusArgs,
        override_job_log_level: int | None,
        origin_span_context: SpanContext,
    ) -> result.Result[None, AlreadyRunningError | StartupError]:
        return self._executor.start(
            self.__class__.__name__,
            self._job_id,
            self._work_dir,
            self.job_prefix,
            target,
            initial_status_args,
            override_job_log_level,
            origin_span_context=SpanContextModel.from_span_context(origin_span_context),
        )

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Wait for background job to be complete.

        Optionally timeout can be given to limit the waiting time. A return value of `True`
        indicates that the job is completed and `False` if it isn't.
        """
        start = time.time()
        while is_active := self.is_active():
            time.sleep(0.5)
            if timeout is not None and time.time() >= start + timeout:
                break

        return not is_active

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
