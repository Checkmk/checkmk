#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs and obseves regular jobs in the cmk.gui context"""

import datetime
import logging
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from setproctitle import setproctitle

from cmk.ccc import store
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.site import get_omd_config, omd_site

from cmk.utils import paths

from cmk.gui import main_modules
from cmk.gui.crash_handler import create_gui_crash_report
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


def main() -> int:
    try:
        setproctitle("cmk-ui-job-scheduler")
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))

        _setup_console_logging()
        init_span_processor(
            trace.init_tracing(omd_site(), "cmk-ui-job-scheduler"),
            exporter_from_config(trace.trace_send_config(get_omd_config(omd_root))),
        )
        add_span_log_handler()

        main_modules.load_plugins()
        if errors := get_failed_plugins():
            raise RuntimeError(f"The following errors occured during plug-in loading: {errors}")

        daemonize()

        with pid_file_lock(_pid_file(omd_root)):
            init_logging()
            _run_scheduler()
    except Exception:
        crash = create_gui_crash_report()
        logger.error(
            "Unhandled exception (Crash ID: %s)",
            crash.ident_to_text(),
            exc_info=True,
        )
        return 1
    return 0


def _setup_console_logging() -> None:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)


def _run_scheduler() -> None:
    while True:
        # gui_context is within the loop to ensure that config changes are automatically applied
        with gui_context(), SuperUserContext():
            try:
                cycle_start = time.time()
                run_scheduled_jobs(list(cron_job_registry.values()))
                time.sleep(60 - (time.time() - cycle_start))
            except Exception:
                crash = create_gui_crash_report()
                logger.error(
                    "Exception in scheduler (Crash ID: %s)",
                    crash.ident_to_text(),
                    exc_info=True,
                )


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
def run_scheduled_jobs(jobs: Sequence[CronJob]) -> None:
    logger.debug("Starting cron jobs")

    for job in _jobs_to_run(jobs, job_runs := _load_last_job_runs()):
        try:
            with tracer.start_as_current_span(
                f"run_cron_job[{job.name}]", attributes={"cmk.gui.job_name": job.name}
            ):
                logger.debug("Starting [%s]", job.name)
                job.callable()
                logger.debug("Finished [%s]", job.name)
        except Exception:
            crash = create_gui_crash_report()
            logger.error(
                "Exception in cron job (Job: %s Crash ID: %s)",
                job.name,
                crash.ident_to_text(),
                exc_info=True,
            )
        job_runs[job.name] = datetime.datetime.now()
    _save_last_job_runs(job_runs)

    logger.debug("Finished all cron jobs")
