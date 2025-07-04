#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
import logging
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from cmk.ccc import store

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.cron import cron_job_registry, CronJob
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context

from cmk import trace

logger = logging.getLogger("cmk.web.ui-job-scheduler")
tracer = trace.get_tracer()


def run_scheduler_threaded(
    crash_report_callback: Callable[[Exception], str],
    stop_event: threading.Event,
    state: SchedulerState,
) -> threading.Thread:
    logger.info("Starting scheduler thread")
    t = threading.Thread(
        target=_run_scheduler,
        args=(crash_report_callback, stop_event, state),
        name="scheduler",
    )
    t.start()
    return t


def _run_scheduler(
    crash_report_callback: Callable[[Exception], str],
    stop_event: threading.Event,
    state: SchedulerState,
) -> None:
    logger.info("Started scheduler")
    while not stop_event.is_set():
        try:
            cycle_start = time.time()
            _collect_finished_threads(state.running_jobs)

            try:
                run_scheduled_jobs(list(cron_job_registry.values()), state, crash_report_callback)
            except Exception as exc:
                crash_msg = crash_report_callback(exc)
                logger.error("Exception in scheduler (Crash ID: %s)", crash_msg, exc_info=True)

            if (sleep_time := 5 - (time.time() - cycle_start)) > 0:
                state.next_cycle_start = int(time.time() + sleep_time)
                stop_event.wait(sleep_time)
        finally:
            # The UI code does not clean up locks properly in all cases, so we need to do it here
            # in case there were some locks left over
            store.release_all_locks()

    logger.info("Waiting for jobs to finish")
    _wait_for_job_threads(state.running_jobs)
    logger.info("Stopped scheduler")


def _last_job_runs_file_path() -> Path:
    return paths.var_dir / "last_job_runs.mk"


def _load_last_job_runs() -> dict[str, datetime.datetime]:
    return {
        ident: datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
        for ident, ts in store.load_object_from_file(
            _last_job_runs_file_path(),
            default={},
        ).items()
    }


def _save_last_job_runs(runs: Mapping[str, datetime.datetime]) -> None:
    store.save_object_to_file(
        _last_job_runs_file_path(),
        {ident: dt.timestamp() for ident, dt in runs.items()},
    )


def reset_scheduling(job_id: str) -> None:
    with store.locked(_last_job_runs_file_path()):
        _save_last_job_runs(
            {
                ident: datetime
                for ident, datetime in _load_last_job_runs().items()
                if ident != job_id
            }
        )


def _jobs_to_run(jobs: Sequence[CronJob], job_runs: dict[str, datetime.datetime]) -> list[CronJob]:
    return [
        job
        for job in jobs
        if job.name not in job_runs
        or datetime.datetime.now(tz=datetime.UTC) >= job_runs[job.name] + job.interval
    ]


def _run_scheduled_jobs(
    jobs: Sequence[CronJob],
    state: SchedulerState,
    crash_report_callback: Callable[[Exception], str],
    job_runs: dict[str, datetime.datetime],
) -> None:
    for job in _jobs_to_run(jobs, job_runs):
        try:
            if job.name in state.running_jobs:
                logger.debug("Skipping [%s] as it is already running", job.name)
                continue

            with tracer.span(
                f"run_cron_job[{job.name}]",
                attributes={
                    "cmk.gui.job_name": job.name,
                    "cmk.gui.job_run_in_thread": str(job.run_in_thread),
                    "cmk.gui.job_interval": str(job.interval.total_seconds()),
                },
            ) as span:
                state.job_executions[job.name] += 1
                if job.run_in_thread:
                    logger.debug("Starting [%s] in thread", job.name)
                    state.running_jobs[job.name] = ScheduledJob(
                        started_at=int(time.time()),
                        thread=(
                            thread := threading.Thread(
                                target=job_thread_main,
                                args=(
                                    job,
                                    trace.Link(span.get_span_context()),
                                    crash_report_callback,
                                ),
                                name=f"scheduled-{job.name}",
                            )
                        ),
                    )
                    thread.start()
                    logger.debug("Started [%s]", job.name)
                else:
                    logger.debug("Starting [%s] unthreaded", job.name)
                    with gui_context(), SuperUserContext():
                        job.callable(active_config)
                    logger.debug("Finished [%s]", job.name)
        except Exception as exc:
            crash_msg = crash_report_callback(exc)
            logger.error(
                "Exception in cron job (Job: %s Crash ID: %s)",
                job.name,
                crash_msg,
                exc_info=True,
            )
        job_runs[job.name] = datetime.datetime.now()


@tracer.instrument()
def run_scheduled_jobs(
    jobs: Sequence[CronJob],
    state: SchedulerState,
    crash_report_callback: Callable[[Exception], str],
) -> None:
    logger.debug("Starting cron jobs")

    with store.locked(_last_job_runs_file_path()):
        last_job_runs = _load_last_job_runs()
        _run_scheduled_jobs(jobs, state, crash_report_callback, last_job_runs)
        _save_last_job_runs(last_job_runs)

    logger.debug("Finished all cron jobs")


def job_thread_main(
    job: CronJob, origin_span: trace.Link, crash_report_callback: Callable[[Exception], str]
) -> None:
    try:
        with (
            tracer.span(
                f"job_thread_main[{job.name}]",
                attributes={"cmk.gui.job_name": job.name},
                links=[origin_span],
            ),
            gui_context(),
            SuperUserContext(),
        ):
            job.callable(active_config)
    except Exception as exc:
        crash_msg = crash_report_callback(exc)
        logger.error(
            "Exception in cron job thread (Job: %s Crash ID: %s)",
            job.name,
            crash_msg,
            exc_info=True,
        )
    finally:
        # The UI code does not clean up locks properly in all cases, so we need to do it here
        # in case there were some locks left over
        store.release_all_locks()


@tracer.instrument()
def _wait_for_job_threads(running_jobs: dict[str, ScheduledJob]) -> None:
    logger.debug("Waiting for threads to terminate")
    for job_name, job in list(running_jobs.items()):
        job.thread.join()
        del running_jobs[job_name]


def _collect_finished_threads(running_jobs: dict[str, ScheduledJob]) -> None:
    for job_name, job in list(running_jobs.items()):
        if not job.thread.is_alive():
            logger.debug("Removing finished thread [%s]", job_name)
            del running_jobs[job_name]


def filter_running_jobs(running_jobs: Mapping[str, ScheduledJob]) -> dict[str, ScheduledJob]:
    """Provide an up-to-date list of running jobs.

    collect_finished_threads might have not been executed since a job finished, which
    causes some lag in the update of scheduler_state.running_jobs. This function
    does some ad-hoc filtering to get the correct list of running jobs.
    """
    return {job_id: job for job_id, job in running_jobs.items() if job.thread.is_alive()}


@dataclass
class ScheduledJob:
    started_at: int
    thread: threading.Thread


@dataclass
class SchedulerState:
    next_cycle_start: int = 0
    running_jobs: dict[str, ScheduledJob] = field(default_factory=dict)
    job_executions: Counter[str] = field(default_factory=Counter)
