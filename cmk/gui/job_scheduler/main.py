#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"

import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import override

from setproctitle import setproctitle

import cmk.ccc.version as cmk_version
from cmk import trace
from cmk.ccc import crash_reporting
from cmk.ccc.crash_reporting import make_crash_report_base_path
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import get_omd_config, omd_site, resource_attributes_from_config
from cmk.gui import log, single_global_setting
from cmk.gui.background_job import job_registry, ThreadedJobExecutor
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.trace.logs import add_span_log_handler
from cmk.utils import paths

from ._fast_api_app import get_application, make_process_health
from ._scheduler import run_scheduler_threaded, SchedulerState
from ._server import default_config, run_server

"""Runs and observes regular jobs in the cmk.gui context"""


def _pid_file(omd_root: Path) -> Path:
    return omd_root / "tmp" / "run" / "cmk-ui-job-scheduler.pid"


class JobSchedulerCrashReport(crash_reporting.ABCCrashReport[None]):
    @override
    @classmethod
    def type(cls) -> str:
        return "ui-job-scheduler"


def default_crash_report_callback(_exc: Exception) -> str:
    crash = JobSchedulerCrashReport(
        crash_report_base_path=make_crash_report_base_path(paths.omd_root),
        crash_info=JobSchedulerCrashReport.make_crash_info(
            cmk_version.get_general_version_infos(paths.omd_root), None
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

        # This is only an intermediate handler until gunicorn run_server sets its own handler
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

        daemonize()

        _setup_file_logging(log_path / "ui-job-scheduler.log")
        logger = logging.getLogger("cmk.web.ui-job-scheduler")
        logger.info("--- Starting ui-job-scheduler (Checkmk %s) ---", cmk_version.__version__)

        with pid_file_lock(_pid_file(omd_root)):
            init_span_processor(
                trace.init_tracing(
                    service_namespace="",
                    service_name="cmk-ui-job-scheduler",
                    service_instance_id=omd_site(),
                    extra_resource_attributes=resource_attributes_from_config(omd_root),
                ),
                exporter_from_config(
                    exporter_log_level=logging.ERROR,
                    config=trace.trace_send_config(get_omd_config(omd_root)),
                ),
            )
            add_span_log_handler()

            loaded_at = int(time.time())

            # The import and load_pugins take a few seconds and we don't want to delay the
            # pre-daemonize phase with this, because it also slows down "omd start" significantly.
            from cmk.gui import main_modules

            if errors := main_modules.get_failed_plugins():
                logger.error("The following errors occurred during plug-in loading: %r", errors)

            scheduler_thread = run_scheduler_threaded(
                crash_report_callback,
                (stop_event := threading.Event()),
                (scheduler_state := SchedulerState()),
            )

            try:
                run_server(
                    default_config(omd_root, run_path, log_path),
                    get_application(
                        logger=logger,
                        loaded_at=loaded_at,
                        process_health=make_process_health,
                        registered_jobs=dict(job_registry.items()),
                        executor=ThreadedJobExecutor(logger),
                        scheduler_state=scheduler_state,
                    ),
                    logger,
                )
            except SystemExit as exc:
                logger.info("Process terminated (Exit code: %d)", exc.code)
                raise
            finally:
                logger.info("Stopping application")
                stop_event.set()
                scheduler_thread.join()
    except MKGeneralException as exc:
        logger.error("ERROR: %s", exc)
        return 1
    except SystemExit:
        raise
    except Exception as exc:
        crash_msg = crash_report_callback(exc)
        logger.error("Unhandled exception (Crash ID: %s)", crash_msg, exc_info=True)
        return 1
    return 0


def _setup_console_logging() -> None:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logging.getLogger().addHandler(handler)


def _setup_file_logging(log_file: Path) -> None:
    handler = logging.FileHandler(log_file, encoding="UTF-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelno)s] [%(process)d/%(threadName)s] %(message)s")
    )
    root_logger = logging.getLogger()
    del root_logger.handlers[:]  # Remove all previously existing handlers
    root_logger.addHandler(handler)
    # Will be overwritten later by set_log_levels calls made during the gui_context initialization
    log.set_log_levels(single_global_setting.load_gui_log_levels())
