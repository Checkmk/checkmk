#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import cmk.utils.resulttype as result

from cmk.trace import get_current_span, get_tracer

from ._interface import JobParameters, JobTarget, SpanContextModel

tracer = get_tracer()


class StartupError(Exception): ...


@dataclass
class RunningJob:
    started_at: int
    thread: threading.Thread
    stop_event: threading.Event


class JobExecutor(Protocol):
    def __init__(self, logger: logging.Logger) -> None: ...

    def start(
        self,
        job_id: str,
        work_dir: str,
        span_id: str,
        target: JobTarget,
        lock_wato: bool,
        is_stoppable: bool,
        override_job_log_level: int | None,
        origin_span_context: SpanContextModel,
    ) -> result.Result[None, StartupError]: ...

    def terminate(self, job_id: str) -> None: ...

    def is_alive(self, job_id: str) -> bool: ...

    def all_running_jobs(self) -> dict[str, int]: ...


class ThreadedJobExecutor(JobExecutor):
    job_initializiation_lock = threading.Lock()
    running_jobs: dict[str, RunningJob] = {}

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @tracer.instrument()
    def start(
        self,
        job_id: str,
        work_dir: str,
        span_id: str,
        target: JobTarget,
        lock_wato: bool,
        is_stoppable: bool,
        override_job_log_level: int | None,
        origin_span_context: SpanContextModel,
    ) -> result.Result[None, StartupError]:
        get_current_span().set_attribute("cmk.job_id", job_id)
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
                    lock_wato=lock_wato,
                    is_stoppable=is_stoppable,
                    override_job_log_level=override_job_log_level,
                    span_id=span_id,
                    origin_span_context=origin_span_context,
                ),
            ),
            name=f"bg-{job_id}",
        )
        ThreadedJobExecutor.running_jobs[job_id] = RunningJob(
            thread=p,
            stop_event=stop_event,
            started_at=int(time.time()),
        )
        p.start()
        return result.OK(None)

    def terminate(self, job_id: str) -> None:
        try:
            self._logger.debug("Stop job %s using stop event", job_id)
            ThreadedJobExecutor.running_jobs[job_id].stop_event.set()
            self._logger.debug("Wait for job to finish")
            ThreadedJobExecutor.running_jobs[job_id].thread.join()
            del ThreadedJobExecutor.running_jobs[job_id]
        except KeyError:
            pass

    def is_alive(self, job_id: str) -> bool:
        try:
            return bool(ThreadedJobExecutor.running_jobs[job_id].thread.is_alive())
        except KeyError:
            return False

    def all_running_jobs(self) -> dict[str, int]:
        ThreadedJobExecutor.clean_up_finished_jobs()
        return {job_id: job.started_at for job_id, job in ThreadedJobExecutor.running_jobs.items()}

    @classmethod
    def clean_up_finished_jobs(cls) -> None:
        for job_id, job in list(cls.running_jobs.items()):
            if not job.thread.is_alive():
                del cls.running_jobs[job_id]
