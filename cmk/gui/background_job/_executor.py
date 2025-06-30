#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import logging
import os
import shutil
import threading
import time
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from typing import override, Protocol

import cmk.ccc.resulttype as result

from cmk.gui.job_scheduler_client import StartupError

from cmk.trace import get_current_span, get_tracer

from ._interface import JobParameters, JobTarget, SpanContextModel
from ._status import InitialStatusArgs, JobStatusSpec, JobStatusStates
from ._store import JobStatusStore

tracer = get_tracer()


class AlreadyRunningError(Exception): ...


@dataclass
class RunningJob:
    started_at: int
    thread: threading.Thread
    stop_event: threading.Event


class JobExecutor(Protocol):
    def __init__(self, logger: logging.Logger) -> None: ...

    def start(
        self,
        type_id: str,
        job_id: str,
        work_dir: str,
        span_id: str,
        target: JobTarget,
        initial_status_args: InitialStatusArgs,
        override_job_log_level: int | None,
        origin_span_context: SpanContextModel,
    ) -> result.Result[None, StartupError | AlreadyRunningError]: ...

    def terminate(self, job_id: str) -> result.Result[None, StartupError]: ...

    def is_alive(self, job_id: str) -> result.Result[bool, StartupError]: ...

    def all_running_jobs(self) -> dict[str, int]: ...

    def job_executions(self) -> dict[str, int]: ...


class ThreadedJobExecutor(JobExecutor):
    job_initializiation_lock = threading.Lock()
    running_jobs: dict[str, RunningJob] = {}
    _job_executions: Counter[str] = Counter()

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._start_lock = threading.Lock()

    @tracer.instrument()
    @override
    def start(
        self,
        type_id: str,
        job_id: str,
        work_dir: str,
        span_id: str,
        target: JobTarget,
        initial_status_args: InitialStatusArgs,
        override_job_log_level: int | None,
        origin_span_context: SpanContextModel,
    ) -> result.Result[None, StartupError | AlreadyRunningError]:
        get_current_span().set_attribute("cmk.job_id", job_id)

        with self._start_lock:
            if (
                job_id in ThreadedJobExecutor.running_jobs
                and ThreadedJobExecutor.running_jobs[job_id].thread.is_alive()
            ):
                return result.Error(AlreadyRunningError(f"Background Job {job_id} already running"))

            self._initialize_work_dir(work_dir, initial_status_args)

            p = threading.Thread(
                # The import hack here is done to avoid circular imports. Actually run_process is
                # only needed in the background job. A better way to approach this, could be to
                # launch the background job with a subprocess instead to get rid of this import
                # hack.
                # TODO
                target=importlib.import_module("cmk.gui.background_job._process").run_process,
                args=(
                    JobParameters(
                        stop_event=(stop_event := threading.Event()),
                        work_dir=work_dir,
                        job_id=job_id,
                        target=target,
                        lock_wato=initial_status_args.lock_wato,
                        is_stoppable=initial_status_args.stoppable,
                        override_job_log_level=override_job_log_level,
                        span_id=span_id,
                        origin_span_context=origin_span_context,
                    ),
                ),
                name=f"bg-{job_id}",
            )
            ThreadedJobExecutor._job_executions[type_id] += 1
            ThreadedJobExecutor.running_jobs[job_id] = RunningJob(
                thread=p,
                stop_event=stop_event,
                started_at=int(time.time()),
            )
            p.start()
        return result.OK(None)

    def _initialize_work_dir(self, work_dir: str, initial_status_args: InitialStatusArgs) -> None:
        with suppress(FileNotFoundError):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)

        JobStatusStore(work_dir).write(
            JobStatusSpec(
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
                title=initial_status_args.title,
                stoppable=initial_status_args.stoppable,
                deletable=initial_status_args.deletable,
                user=initial_status_args.user,
                estimated_duration=initial_status_args.estimated_duration,
                logfile_path=initial_status_args.logfile_path,
                lock_wato=initial_status_args.lock_wato,
                host_name=initial_status_args.host_name,
            )
        )

    @override
    def terminate(self, job_id: str) -> result.Result[None, StartupError]:
        try:
            self._logger.debug("Stop job %s using stop event", job_id)
            ThreadedJobExecutor.running_jobs[job_id].stop_event.set()
            self._logger.debug("Wait for job to finish")
            ThreadedJobExecutor.running_jobs[job_id].thread.join()
            del ThreadedJobExecutor.running_jobs[job_id]
        except KeyError:
            pass
        return result.OK(None)

    @override
    def is_alive(self, job_id: str) -> result.Result[bool, StartupError]:
        try:
            return result.OK(bool(ThreadedJobExecutor.running_jobs[job_id].thread.is_alive()))
        except KeyError:
            return result.OK(False)

    @override
    def all_running_jobs(self) -> dict[str, int]:
        ThreadedJobExecutor.clean_up_finished_jobs()
        return {job_id: job.started_at for job_id, job in ThreadedJobExecutor.running_jobs.items()}

    @classmethod
    def clean_up_finished_jobs(cls) -> None:
        for job_id, job in list(cls.running_jobs.items()):
            if not job.thread.is_alive():
                del cls.running_jobs[job_id]

    @override
    def job_executions(self) -> dict[str, int]:
        return dict(ThreadedJobExecutor._job_executions)
