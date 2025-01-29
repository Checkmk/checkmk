#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import logging
import threading
from dataclasses import dataclass
from typing import Protocol

from ._interface import JobParameters, JobTarget, SpanContextModel


@dataclass
class RunningJob:
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
    ) -> None: ...

    def terminate(self, job_id: str) -> None: ...

    def is_alive(self, job_id: str) -> bool: ...


class ThreadedJobExecutor(JobExecutor):
    running_jobs: dict[str, RunningJob] = {}

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

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
    ) -> None:
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
        ThreadedJobExecutor.running_jobs[job_id] = RunningJob(thread=p, stop_event=stop_event)
        p.start()

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
