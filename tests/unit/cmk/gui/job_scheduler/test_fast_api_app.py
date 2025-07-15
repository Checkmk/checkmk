#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import threading
from collections import Counter

from fastapi.testclient import TestClient

import cmk.ccc.resulttype as result

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    HealthResponse,
    InitialStatusArgs,
    IsAliveRequest,
    IsAliveResponse,
    JobExecutor,
    JobTarget,
    NoArgs,
    ProcessHealth,
    SpanContextModel,
    StartRequest,
    StartResponse,
    TerminateRequest,
)
from cmk.gui.job_scheduler._fast_api_app import get_application
from cmk.gui.job_scheduler._scheduler import ScheduledJob, SchedulerState
from cmk.gui.job_scheduler_client import StartupError

logger = logging.getLogger(__name__)


class DummyExecutor(JobExecutor):
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
        origin_span: SpanContextModel,
    ) -> result.Result[None, StartupError]:
        return result.OK(None)

    def terminate(self, job_id: str) -> result.Result[None, StartupError]:
        return result.OK(None)

    def is_alive(self, job_id: str) -> result.Result[bool, StartupError]:
        return result.OK(True)

    def all_running_jobs(self) -> dict[str, int]:
        return {
            "job_id": 42,
        }

    def job_executions(self) -> dict[str, int]:
        return {
            "job_1": 1,
            "job_2": 2,
        }


class HelloJob(BackgroundJob):
    job_prefix = "hello"
    on_scheduler_start_called = False

    @classmethod
    def gui_title(cls) -> str:
        return "Hello Job"

    @classmethod
    def on_scheduler_start(cls, executor: JobExecutor, *, debug: bool) -> None:
        HelloJob.on_scheduler_start_called = True


class DummyThread(threading.Thread):
    def __init__(self, is_stopped: bool) -> None:
        super().__init__()
        self._is_stopped = is_stopped

    def is_alive(self) -> bool:
        return not self._is_stopped


def _get_test_client(loaded_at: int) -> TestClient:
    return TestClient(
        get_application(
            logger,
            loaded_at=loaded_at,
            process_health=lambda: ProcessHealth(
                pid=1337,
                ppid=1338,
                num_fds=42,
                vm_bytes=1000,
                rss_bytes=1234,
            ),
            registered_jobs={"hello_job": HelloJob},
            executor=DummyExecutor(logger),
            scheduler_state=SchedulerState(
                next_cycle_start=10,
                running_jobs={
                    "scheduled_1_running": ScheduledJob(
                        started_at=123,
                        thread=DummyThread(is_stopped=False),
                    ),
                    "scheduled_2_finished": ScheduledJob(
                        started_at=111,
                        thread=DummyThread(is_stopped=True),
                    ),
                },
                job_executions=Counter({"scheduled_1": 1, "scheduled_2": 2}),
            ),
        )
    )


def job_test_target(job_interface: BackgroundProcessInterface, args: NoArgs) -> None:
    pass


def test_start() -> None:
    with _get_test_client(loaded_at=1337) as client:
        job_target: JobTarget = JobTarget(
            callable=job_test_target,
            args=NoArgs().model_dump(mode="json"),
        )
        resp = client.post(
            "start",
            json=StartRequest(
                type_id="HelloJob",
                job_id="hi",
                work_dir="/tmp",
                span_id="no_span",
                target=job_target,
                initial_status_args=InitialStatusArgs(
                    title="Hi",
                    deletable=False,
                    stoppable=False,
                    lock_wato=False,
                    user=None,
                ),
                override_job_log_level=None,
                origin_span_context=SpanContextModel(
                    trace_id=0,
                    span_id=0,
                    is_remote=False,
                    trace_flags=0,
                    trace_state=[],
                ),
            ).model_dump(mode="json"),
        )

    assert resp.status_code == 200
    assert StartResponse.model_validate(resp.json()).success is True


def test_terminate() -> None:
    with _get_test_client(loaded_at=1337) as client:
        resp = client.post(
            "terminate", json=TerminateRequest(job_id="test").model_dump(mode="json")
        )

    assert resp.status_code == 200
    assert resp.text == "null"


def test_is_alive() -> None:
    with _get_test_client(loaded_at=1337) as client:
        resp = client.post("is_alive", json=IsAliveRequest(job_id="test").model_dump(mode="json"))

    assert resp.status_code == 200
    assert IsAliveResponse.model_validate(resp.json()).is_alive is True


def test_health_check() -> None:
    with _get_test_client(loaded_at=(loaded_at := 1337)) as client:
        resp = client.get("health")

    assert resp.status_code == 200
    response = HealthResponse.model_validate(resp.json())
    assert response.loaded_at == loaded_at
    assert response.process == ProcessHealth(
        pid=1337,
        ppid=1338,
        num_fds=42,
        vm_bytes=1000,
        rss_bytes=1234,
    )
    assert response.background_jobs.running_jobs == {"job_id": 42}
    assert response.background_jobs.job_executions == {"job_1": 1, "job_2": 2}
    assert response.scheduled_jobs.next_cycle_start == 10
    assert response.scheduled_jobs.running_jobs == {"scheduled_1_running": 123}
    assert response.scheduled_jobs.job_executions == {"scheduled_1": 1, "scheduled_2": 2}


def test_on_scheduler_start_executed() -> None:
    HelloJob.on_scheduler_start_called = False
    with _get_test_client(loaded_at=1337):
        assert HelloJob.on_scheduler_start_called is True


def test_reset_scheduling() -> None:
    with _get_test_client(loaded_at=1337) as client:
        resp = client.post("reset_scheduling", json={"job_id": "foo_bar"})

    assert resp.status_code == 200
    assert resp.text == "null"
