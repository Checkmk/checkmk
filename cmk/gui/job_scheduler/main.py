#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from setproctitle import setproctitle

import cmk.ccc.version as cmk_version
from cmk.ccc import crash_reporting
from cmk.ccc.crash_reporting import VersionInfo
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.site import get_omd_config, omd_site, resource_attributes_from_config

from cmk.utils import paths

from cmk.gui.background_job import job_registry, ThreadedJobExecutor
from cmk.gui.log import logger
from cmk.gui.utils import get_failed_plugins

from cmk import trace
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.trace.logs import add_span_log_handler

from ._background_jobs import default_config, get_application, run_server
from ._scheduler import run_scheduler_threaded

"""Runs and observes regular jobs in the cmk.gui context"""


def _pid_file(omd_root: Path) -> Path:
    return omd_root / "tmp" / "run" / "cmk-ui-job-scheduler.pid"


class JobSchedulerCrashReport(crash_reporting.ABCCrashReport[VersionInfo]):
    @classmethod
    def type(cls) -> str:
        return "ui-job-scheduler"


def default_crash_report_callback(_exc: Exception) -> str:
    crash = JobSchedulerCrashReport(
        paths.crash_dir,
        JobSchedulerCrashReport.make_crash_info(
            cmk_version.get_general_version_infos(paths.omd_root)
        ),
    )
    crash_reporting.CrashReportStore().save(crash)
    return crash.ident_to_text()


def main(crash_report_callback: Callable[[Exception], str]) -> int:
    try:
        setproctitle("cmk-ui-job-scheduler")
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))
        run_path = omd_root / "tmp" / "run"
        log_path = omd_root / "var" / "log" / "ui-job-scheduler"

        run_path.mkdir(exist_ok=True, parents=True)
        log_path.mkdir(exist_ok=True, parents=True)

        _setup_console_logging()

        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

        daemonize()

        with pid_file_lock(_pid_file(omd_root)):
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

            loaded_at = int(time.time())

            # The import and load_pugins take a few seconds and we don't want to delay the
            # pre-daemonize phase with this, because it also slows down "omd start" significantly.
            from cmk.gui import main_modules

            main_modules.load_plugins()
            if errors := get_failed_plugins():
                raise RuntimeError(f"The following errors occured during plug-in loading: {errors}")

            _setup_file_logging(log_path / "ui-job-scheduler.log")
            scheduler_thread = run_scheduler_threaded(
                crash_report_callback, (stop_event := threading.Event())
            )

            try:
                run_server(
                    default_config(omd_root, run_path, log_path),
                    get_application(
                        logger=logger,
                        loaded_at=loaded_at,
                        registered_jobs=dict(job_registry.items()),
                        executor=ThreadedJobExecutor(logger),
                    ),
                )
            finally:
                stop_event.set()
                scheduler_thread.join()
    except Exception as exc:
        crash_msg = crash_report_callback(exc)
        logger.error("Unhandled exception (Crash ID: %s)", crash_msg, exc_info=True)
        return 1
    return 0


def _setup_console_logging() -> None:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)


def _setup_file_logging(log_file: Path) -> None:
    handler = logging.FileHandler(log_file, encoding="UTF-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelno)s] [%(process)d/%(threadName)s] %(message)s")
    )
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
