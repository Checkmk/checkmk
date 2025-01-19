#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs and observes regular jobs in the cmk.gui context"""

import datetime
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from setproctitle import setproctitle

import cmk.ccc.version as cmk_version
from cmk.ccc import crash_reporting, store
from cmk.ccc.crash_reporting import VersionInfo
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.site import get_omd_config, omd_site, resource_attributes_from_config

from cmk.utils import paths

from cmk.gui.cron import cron_job_registry, CronJob
from cmk.gui.log import init_logging, logger
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context

from cmk import trace
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.trace.logs import add_span_log_handler

tracer = trace.get_tracer()


def _pid_file(omd_root: Path) -> Path:
    return omd_root / "tmp" / "run" / "cmk-ui-job-scheduler.pid"


class JobSchedulerCrashReport(crash_reporting.ABCCrashReport[VersionInfo]):
    @classmethod
    def type(cls) -> str:
        return "ui-job-scheduler"


def default_crash_report_callback(_exc: Exception) -> str:
    crash = JobSchedulerCrashReport.from_exception(
        paths.crash_dir,
        cmk_version.get_general_version_infos(paths.omd_root),
    )
    crash_reporting.CrashReportStore().save(crash)
    return crash.ident_to_text()


def main(crash_report_callback: Callable[[Exception], str]) -> int:
    try:
        setproctitle("cmk-ui-job-scheduler")
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))

        _setup_console_logging()
        init_span_processor(
            trace.init_tracing(
                service_namespace="",
                service_name="cmk-ui-job-scheduler",
                service_instance_id=omd_site(),
                extra_resource_attributes=resource_attributes_from_config(omd_root),
            ),
            exporter_from_config(trace.trace_send_config(get_omd_config(omd_root))),
        )
        add_span_log_handler()

        daemonize()

        # The import and load_pugins take a few seconds and we don't want to delay the
        # pre-daemonize phase with this, because it also slows down "omd start" significantly.
        from cmk.gui import main_modules

        main_modules.load_plugins()
        if errors := get_failed_plugins():
            raise RuntimeError(f"The following errors occured during plug-in loading: {errors}")

        with pid_file_lock(_pid_file(omd_root)):
            init_logging()
            _run_scheduler(crash_report_callback)
    except Exception as exc:
        crash_msg = crash_report_callback(exc)
        logger.error("Unhandled exception (Crash ID: %s)", crash_msg, exc_info=True)
        return 1
    return 0


def _setup_console_logging() -> None:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)


def _run_scheduler(crash_report_callback: Callable[[Exception], str]) -> None:
    job_threads: dict[str, threading.Thread] = {}
    while True:
        cycle_start = time.time()
        _collect_finished_threads(job_threads)

        try:
            run_scheduled_jobs(list(cron_job_registry.values()), job_threads, crash_report_callback)
        except Exception as exc:
            crash_msg = crash_report_callback(exc)
            logger.error("Exception in scheduler (Crash ID: %s)", crash_msg, exc_info=True)

        if (sleep_time := 60 - (time.time() - cycle_start)) > 0:
            time.sleep(sleep_time)
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
