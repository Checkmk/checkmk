#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide an interface to the automation helper"""

import logging
import socket
from collections.abc import Sequence
from typing import Final

import requests
from pydantic import BaseModel
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

from cmk.utils import paths

from ._executor import JobExecutor
from ._interface import JobTarget, SpanContextModel
from ._models import HealthResponse

JOB_SCHEDULER_HOST: Final = "localhost"
JOB_SCHEDULER_BASE_URL: Final = "http://local-ui-job-scheduler"
JOB_SCHEDULER_ENDPOINT: Final = f"{JOB_SCHEDULER_BASE_URL}/automation"
JOB_SCHEDULER_SOCKET: Final = "tmp/run/ui-job-scheduler.sock"


class JobSchedulerExecutor(JobExecutor):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._session = requests.Session()
        self._session.mount(JOB_SCHEDULER_BASE_URL, _LocalAutomationAdapter())

    def start(
        self,
        job_id: str,
        work_dir: str,
        span_id: str,
        target: JobTarget,
        lock_wato: bool,
        is_stoppable: bool,
        override_job_log_level: int | None,
        origin_span: SpanContextModel,
    ) -> None: ...

    def terminate(self, job_id: str) -> None: ...

    def is_alive(self, job_id: str) -> bool:
        return True

    def health(self) -> HealthResponse:
        response = self._session.get(JOB_SCHEDULER_BASE_URL + "/health")
        response.raise_for_status()
        response_data = response.json()
        return HealthResponse.model_validate(response_data)


class _AutomationPayload(BaseModel, frozen=True):
    name: str
    args: Sequence[str]
    stdin: str
    log_level: int


class _LocalAutomationConnection(HTTPConnection):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(paths.omd_root.joinpath(JOB_SCHEDULER_SOCKET)))


class _LocalAutomationConnectionPool(HTTPConnectionPool):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    def _new_conn(self) -> _LocalAutomationConnection:
        return _LocalAutomationConnection()


class _LocalAutomationAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):  # type: ignore[no-untyped-def]
        return _LocalAutomationConnectionPool()
