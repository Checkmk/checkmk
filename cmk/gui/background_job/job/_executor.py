#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import logging
from typing import Protocol

import cmk.ccc.resulttype as result
from cmk.gui.job_scheduler_client import StartupError

from ._interface import JobTarget, SpanContextModel
from ._status import InitialStatusArgs


class AlreadyRunningError(Exception): ...


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
