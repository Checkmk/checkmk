#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Background job process entry point.

This must not be imported from anywhere outside of the background job process."""

from __future__ import annotations

import io
import os
import signal
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from logging import Formatter, Logger, StreamHandler
from pathlib import Path
from types import FrameType
from typing import ContextManager

from setproctitle import setthreadtitle

from cmk.ccc import store
from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.site import get_omd_config, omd_site, resource_attributes_from_config
from cmk.ccc.version import edition

from cmk.utils import paths
from cmk.utils.log import VERBOSE
from cmk.utils.user import UserId

from cmk.gui import log
from cmk.gui.crash_handler import create_gui_crash_report
from cmk.gui.features import features_registry
from cmk.gui.i18n import _
from cmk.gui.session import SuperUserContext, UserContext
from cmk.gui.single_global_setting import load_gui_log_levels
from cmk.gui.utils import get_failed_plugins
from cmk.gui.wsgi.trace import instrument_app_dependencies

from cmk.trace import (
    get_tracer,
    get_tracer_provider,
    init_tracing,
    INVALID_SPAN,
    Link,
    service_namespace_from_config,
    set_span_in_context,
    trace_send_config,
    TracerProvider,
)
from cmk.trace.export import exporter_from_config

from ._app import BackgroundJobFlaskApp
from ._defines import BackgroundJobDefines
from ._interface import BackgroundProcessInterface, JobParameters, JobTarget
from ._status import JobStatusStates
from ._store import JobStatusSpecUpdate, JobStatusStore

tracer = get_tracer()


def run_process(job_parameters: JobParameters) -> None:
    (
        work_dir,
        job_id,
        target,
        lock_wato,
        is_stoppable,
        override_job_log_level,
        span_id,
        init_span_processor_callback,
        origin_span_context,
    ) = job_parameters

    logger = log.logger.getChild("background-job")
    jobstatus_store = JobStatusStore(work_dir)
    _detach_from_parent()

    final_status_update: JobStatusSpecUpdate = {}
    try:
        job_status = jobstatus_store.read()
        init_span_processor_callback(
            init_tracing(
                service_namespace=service_namespace_from_config(
                    "", omd_config := get_omd_config(paths.omd_root)
                ),
                service_name="gui",
                service_instance_id=omd_site(),
                extra_resource_attributes=resource_attributes_from_config(paths.omd_root),
            ),
            exporter_from_config(trace_send_config(omd_config)),
        )
        instrument_app_dependencies()
        _initialize_environment(
            logger, job_id, Path(work_dir), lock_wato, is_stoppable, override_job_log_level
        )

        with tracer.span(
            f"run_process[{span_id}]",
            context=set_span_in_context(INVALID_SPAN),
            attributes={
                "cmk.job_id": job_id,
                "cmk.target.callable": str(target.callable),
            },
            links=[Link(origin_span_context.to_span_context())],
        ):
            logger.log(VERBOSE, "Initialized background job (Job ID: %s)", job_id)
            jobstatus_store.update({"pid": os.getpid(), "state": JobStatusStates.RUNNING})

            _execute_function(
                logger,
                target,
                BackgroundProcessInterface(
                    work_dir, job_id, logger, gui_job_context_manager(job_status.user)
                ),
            )

            # Final status update
            job_status = jobstatus_store.read()

            if job_status.loginfo["JobException"]:
                final_state = JobStatusStates.EXCEPTION
            else:
                final_state = JobStatusStates.FINISHED

            final_status_update = {
                "state": final_state,
                "duration": time.time() - job_status.started,
            }

    except MKTerminate:
        logger.warning("Job was stopped")
        final_status_update = {"state": JobStatusStates.STOPPED}
    except Exception:
        crash = create_gui_crash_report()
        logger.error(
            "Exception while preparing background function environment (Crash ID: %s)",
            crash.ident_to_text(),
            exc_info=True,
        )
        final_status_update = {"state": JobStatusStates.EXCEPTION}
    finally:
        # We want to be sure that all spans we created so far are flushed before the background
        # jobs goes into it's final state. There may spans come later. These are handled by an
        # atexit handler, which is registered by opentelemetry, during the finalization of the
        # interpreter, but we want to have all finished spans collected before we set the
        # background job to finished.
        if isinstance(provider := get_tracer_provider(), TracerProvider):
            provider.force_flush()

        jobstatus_store.update(final_status_update)


def gui_job_context_manager(user: str | None) -> Callable[[], ContextManager[None]]:
    @contextmanager
    def gui_job_context() -> Iterator[None]:
        _load_ui()

        try:
            features = features_registry[str(edition(paths.omd_root))]
        except KeyError:
            raise ValueError(f"Invalid edition: {edition}")

        with (
            BackgroundJobFlaskApp(features).test_request_context("/"),
            SuperUserContext() if user is None else UserContext(UserId(user)),
        ):
            yield None

    return gui_job_context


def _load_ui() -> None:
    """This triggers loading all modules of the UI, internal ones and plugins"""
    # Import locally to only have it executed in the background job process and not in the launching
    # process. Moving it to the module level will significantly slow down the launching process.
    from cmk.gui import main_modules

    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


def _register_signal_handlers(logger: Logger, is_stoppable: bool, job_id: str) -> None:
    logger.debug("Register signal handler %d", os.getpid())
    signal.signal(signal.SIGTERM, partial(_handle_sigterm, logger, is_stoppable, job_id))


def _handle_sigterm(
    logger: Logger, is_stoppable: bool, job_id: str, signum: int, frame: FrameType | None
) -> None:
    logger.debug("Received SIGTERM")
    if not is_stoppable:
        logger.warning(
            "Skip termination of background job (Job ID: %s, PID: %d)",
            job_id,
            os.getpid(),
        )
        return

    raise MKTerminate()


def _detach_from_parent() -> None:
    # Detach from parent
    os.setsid()

    # NOTE: Setting the thread title is not for cosmetics! BackgroundJob._is_correct_process()
    # will not do the right thing without it! Furthermore, using setproctitle() instead of
    # setthreadtitle() would be more fragile, because the former will only work if os.environ
    # has not been damaged too much, but our tests do this via mock.patch.dict(os.environ, ...).
    setthreadtitle(BackgroundJobDefines.process_name)


def _initialize_environment(
    logger: Logger,
    job_id: str,
    work_dir: Path,
    lock_wato: bool,
    is_stoppable: bool,
    override_job_log_level: int | None,
) -> None:
    """Setup environment (Logging, Livestatus handles, etc.)"""
    _open_stdout_and_stderr(work_dir)
    _set_log_levels(override_job_log_level)
    _enable_logging_to_stdout()
    _register_signal_handlers(logger, is_stoppable, job_id)
    _lock_configuration(lock_wato)


def _set_log_levels(override_job_log_level: int | None) -> None:
    log.set_log_levels(
        {
            **load_gui_log_levels(),
            **(
                {"cmk.web.background-job": override_job_log_level}
                if override_job_log_level is not None
                else {}
            ),
        }
    )


def _execute_function(
    logger: Logger,
    target: JobTarget,
    job_interface: BackgroundProcessInterface,
) -> None:
    try:
        target.callable(job_interface, target.args)
    except MKTerminate:
        raise
    except Exception as e:
        crash = create_gui_crash_report()
        logger.exception("Exception in background function (Crash ID: %s)", crash.ident_to_text())
        job_interface.send_exception(_("Exception (Crash ID: %s): %s") % (crash.ident_to_text(), e))


def _open_stdout_and_stderr(work_dir: Path) -> None:
    """Create a temporary file and use it as stdout / stderr buffer"""
    # - We can not use io.BytesIO() or similar because we need real file descriptors
    #   to be able to catch the (debug) output of libraries like libldap or subproccesses
    # - Use buffering=0 to make the non flushed output directly visible in
    #   the job progress dialog
    # - Python 3's stdout and stderr expect 'str' not 'bytes'
    unbuffered = (work_dir / BackgroundJobDefines.progress_update_filename).open("wb", buffering=0)
    sys.stdout = sys.stderr = io.TextIOWrapper(unbuffered, write_through=True)
    os.dup2(sys.stdout.fileno(), 1)
    os.dup2(sys.stderr.fileno(), 2)


def _enable_logging_to_stdout() -> None:
    """In addition to the web.log we also want to see the job specific logs
    in stdout (which results in job progress info)"""
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    log.logger.addHandler(handler)


def _lock_configuration(lock_wato: bool) -> None:
    if lock_wato:
        store.release_all_locks()
        store.lock_exclusive(paths.configuration_lockfile)
