#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from cmk.ccc import store

from cmk.utils import paths

from cmk.gui.cron import cron_job_registry, CronJob
from cmk.gui.log import logger
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context

from cmk import trace

tracer = trace.get_tracer()


def run_scheduler_threaded(
    crash_report_callback: Callable[[Exception], str], stop_event: threading.Event
) -> threading.Thread:
    t = threading.Thread(
        target=_run_scheduler,
        args=(crash_report_callback, stop_event),
        name="scheduler",
    )
    t.start()
    return t


def _run_scheduler(
    crash_report_callback: Callable[[Exception], str], stop_event: threading.Event
) -> None:
    job_threads: dict[str, threading.Thread] = {}
    while not stop_event.is_set():
        try:
            cycle_start = time.time()
            _collect_finished_threads(job_threads)

            try:
                run_scheduled_jobs(
                    list(cron_job_registry.values()), job_threads, crash_report_callback
                )
            except Exception as exc:
                crash_msg = crash_report_callback(exc)
                logger.error("Exception in scheduler (Crash ID: %s)", crash_msg, exc_info=True)

            if (sleep_time := 60 - (time.time() - cycle_start)) > 0:
                stop_event.wait(sleep_time)
        finally:
            # The UI code does not clean up locks properly in all cases, so we need to do it here
            # in case there were some locks left over
            store.release_all_locks()

    _wait_for_job_threads(job_threads)


def _load_last_job_runs() -> dict[str, datetime.datetime]:
    return {
        ident: datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
        for ident, ts in store.load_object_from_file(
            Path(paths.var_dir) / "last_job_runs.mk", default={}
        ).items()
    }


def _save_last_job_runs(runs: Mapping[str, datetime.datetime]) -> None:
    store.save_object_to_file(
        Path(paths.var_dir) / "last_job_runs.mk",
        {ident: dt.timestamp() for ident, dt in runs.items()},
    )


def _jobs_to_run(jobs: Sequence[CronJob], job_runs: dict[str, datetime.datetime]) -> list[CronJob]:
    return [
        job
        for job in jobs
        if job.name not in job_runs
        or datetime.datetime.now(tz=datetime.UTC) >= job_runs[job.name] + job.interval
    ]


@tracer.start_as_current_span("run_scheduled_jobs")
def run_scheduled_jobs(
    jobs: Sequence[CronJob],
    job_threads: dict[str, threading.Thread],
    crash_report_callback: Callable[[Exception], str],
) -> None:
    logger.debug("Starting cron jobs")

    for job in _jobs_to_run(jobs, job_runs := _load_last_job_runs()):
        try:
            if job.name in job_threads:
                logger.debug("Skipping [%s] as it is already running", job.name)
                continue

            with tracer.start_as_current_span(
                f"run_cron_job[{job.name}]",
                attributes={
                    "cmk.gui.job_name": job.name,
                    "cmk.gui.job_run_in_thread": str(job.run_in_thread),
                    "cmk.gui.job_interval": str(job.interval.total_seconds()),
                },
            ) as span:
                if job.run_in_thread:
                    logger.debug("Starting [%s] in thread", job.name)
                    job_threads[job.name] = thread = threading.Thread(
                        target=job_thread_main,
                        args=(
                            job,
                            trace.Link(span.get_span_context()),
                            crash_report_callback,
                        ),
                        name=f"scheduled-{job.name}",
                    )
                    thread.start()
                    logger.debug("Started [%s]", job.name)
                else:
                    logger.debug("Starting [%s] unthreaded", job.name)
                    with gui_context(), SuperUserContext():
                        job.callable()
                    logger.debug("Finished [%s]", job.name)
        except Exception as exc:
            crash_msg = crash_report_callback(exc)
            logger.error(
                "Exception in cron job (Job: %s Crash ID: %s)", job.name, crash_msg, exc_info=True
            )
        job_runs[job.name] = datetime.datetime.now()
    _save_last_job_runs(job_runs)

    logger.debug("Finished all cron jobs")


def job_thread_main(
    job: CronJob, origin_span: trace.Link, crash_report_callback: Callable[[Exception], str]
) -> None:
    try:
        with (
            tracer.start_as_current_span(
                f"job_thread_main[{job.name}]",
                attributes={"cmk.gui.job_name": job.name},
                links=[origin_span],
            ),
            gui_context(),
            SuperUserContext(),
        ):
            job.callable()
    except Exception as exc:
        crash_msg = crash_report_callback(exc)
        logger.error(
            "Exception in cron job thread (Job: %s Crash ID: %s)",
            job.name,
            crash_msg,
            exc_info=True,
        )


@tracer.start_as_current_span("wait_for_job_threads")
def _wait_for_job_threads(job_threads: dict[str, threading.Thread]) -> None:
    logger.debug("Waiting for threads to terminate")
    for thread in job_threads.values():
        thread.join()


def _collect_finished_threads(job_threads: dict[str, threading.Thread]) -> None:
    for job_name, thread in list(job_threads.items()):
        if not thread.is_alive():
            logger.debug("Removing finished thread [%s]", job_name)
            del job_threads[job_name]
