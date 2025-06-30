#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide an interface to the automation helper"""

import logging
from typing import override

import cmk.ccc.resulttype as result

from cmk.gui.job_scheduler_client import JobSchedulerClient, StartupError

from ._executor import AlreadyRunningError, JobExecutor
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


class JobSchedulerExecutor(JobExecutor):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._client = JobSchedulerClient()

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
        r = self._client.post(
            "start",
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
        r = self._client.post(
            "terminate",
            json=TerminateRequest(job_id=job_id).model_dump(mode="json"),
        )
        if r.is_error():
            return result.Error(r.error)
        return result.OK(None)

    @override
    def is_alive(self, job_id: str) -> result.Result[bool, StartupError]:
        r = self._client.post(
            "is_alive",
            json=IsAliveRequest(job_id=job_id).model_dump(mode="json"),
        )
        if r.is_error():
            return result.Error(r.error)
        response_data = r.ok.json()
        return result.OK(IsAliveResponse.model_validate(response_data).is_alive)

    def health(self) -> HealthResponse:
        r = self._client.get("health")
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
