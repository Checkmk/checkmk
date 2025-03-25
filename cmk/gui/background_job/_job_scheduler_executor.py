#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide an interface to the automation helper"""

import logging
import socket
from typing import Final, override

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

import cmk.utils.resulttype as result
from cmk.utils import paths

from cmk.gui.i18n import _

from ._executor import AlreadyRunningError, JobExecutor, StartupError
from ._interface import JobTarget, SpanContextModel
from ._models import (
    HealthResponse,
    IsAliveRequest,
    IsAliveResponse,
    StartRequest,
    StartResponse,
    TerminateRequest,
)
from ._status import InitialStatusArgs

JOB_SCHEDULER_HOST: Final = "localhost"
JOB_SCHEDULER_BASE_URL: Final = "http://local-ui-job-scheduler"
JOB_SCHEDULER_ENDPOINT: Final = f"{JOB_SCHEDULER_BASE_URL}/automation"
JOB_SCHEDULER_SOCKET: Final = "tmp/run/ui-job-scheduler.sock"


class JobSchedulerExecutor(JobExecutor):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._session = requests.Session()
        self._session.mount(JOB_SCHEDULER_BASE_URL, _JobSchedulerAdapter())

    @override
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
    ) -> result.Result[None, StartupError | AlreadyRunningError]:
        r = self._post(
            JOB_SCHEDULER_BASE_URL + "/start",
            json=StartRequest(
                type_id=type_id,
                job_id=job_id,
                work_dir=work_dir,
                span_id=span_id,
                target=JobTarget(
                    callable=target.callable,
                    args=target.args.model_dump(mode="json"),
                ),
                initial_status_args=initial_status_args,
                override_job_log_level=override_job_log_level,
                origin_span_context=origin_span_context,
            ).model_dump(mode="json"),
        )
        if r.is_error():
            return result.Error(r.error)
        response = StartResponse.model_validate(r.ok.json())
        if not response.success:
            if response.error_type == "StartupError":
                return result.Error(StartupError(response.error_message))
            elif response.error_type == "AlreadyRunningError":
                return result.Error(AlreadyRunningError(response.error_message))
            raise TypeError(f"Unhandled error: {response.error_type} - {response.error_message}")

        return result.OK(None)

    @override
    def terminate(self, job_id: str) -> result.Result[None, StartupError]:
        r = self._post(
            JOB_SCHEDULER_BASE_URL + "/terminate",
            json=TerminateRequest(job_id=job_id).model_dump(mode="json"),
        )
        if r.is_error():
            return result.Error(r.error)
        return result.OK(None)

    @override
    def is_alive(self, job_id: str) -> result.Result[bool, StartupError]:
        r = self._post(
            JOB_SCHEDULER_BASE_URL + "/is_alive",
            json=IsAliveRequest(job_id=job_id).model_dump(mode="json"),
        )
        if r.is_error():
            return result.Error(r.error)
        response_data = r.ok.json()
        return result.OK(IsAliveResponse.model_validate(response_data).is_alive)

    def health(self) -> HealthResponse:
        r = self._get(JOB_SCHEDULER_BASE_URL + "/health")
        if r.is_error():
            raise r.error
        response_data = r.ok.json()
        return HealthResponse.model_validate(response_data)

    @override
    def all_running_jobs(self) -> dict[str, int]:
        return self.health().background_jobs.running_jobs

    @override
    def job_executions(self) -> dict[str, int]:
        return self.health().background_jobs.job_executions

    def _get(self, url: str) -> result.Result[requests.Response, StartupError]:
        return self._request("GET", url)

    def _post(
        self, url: str, json: dict[str, object]
    ) -> result.Result[requests.Response, StartupError]:
        return self._request("POST", url, json)

    def _request(
        self, method: str, url: str, json: dict[str, object] | None = None
    ) -> result.Result[requests.Response, StartupError]:
        try:
            response = self._session.request(method, url, json=json, timeout=30)
        except requests.ConnectionError as e:
            return result.Error(
                StartupError(
                    _(
                        "Could not connect to ui-job-scheduler. "
                        "Possibly the service <tt>ui-job-scheduler</tt> is not started, "
                        "please make sure that all site services are all started. "
                        "Tried to connect via <tt>%s</tt>. Reported error was: %s."
                    )
                    % (paths.omd_root.joinpath(JOB_SCHEDULER_SOCKET), e)
                )
            )
        except requests.RequestException as e:
            return result.Error(
                StartupError(_("Communication with ui-job-scheduler failed: %s") % e)
            )

        if response.status_code != 200:
            return result.Error(
                StartupError(_("Got response: HTTP %s: %s") % (response.status_code, response.text))
            )

        return result.OK(response)


class _JobSchedulerConnection(HTTPConnection):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    @override
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(paths.omd_root.joinpath(JOB_SCHEDULER_SOCKET)))


class _JobSchedulerConnectionPool(HTTPConnectionPool):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    def _new_conn(self) -> _JobSchedulerConnection:
        return _JobSchedulerConnection()


class _JobSchedulerAdapter(HTTPAdapter):
    @override
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):  # type: ignore[no-untyped-def]
        return _JobSchedulerConnectionPool()
