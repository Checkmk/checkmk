#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import threading
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from opentelemetry import trace as otel_trace
from pydantic import BaseModel

from tests.testlib.common.utils import wait_until

import cmk.ccc.version as cmk_version

import cmk.utils.log
import cmk.utils.paths

import cmk.gui.log
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobDefines,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
    JobStatusStates,
    JobTarget,
    NoArgs,
    running_job_ids,
    simple_job_target,
    wait_for_background_jobs,
)

from cmk.trace import get_tracer, init_tracing, ReadableSpan
from cmk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

tracer = get_tracer()


def test_registered_background_jobs() -> None:
    expected_jobs = [
        "ActivateChangesSchedulerBackgroundJob",
        "ParentScanBackgroundJob",
        "RenameHostsBackgroundJob",
        "RenameHostBackgroundJob",
        "FetchAgentOutputBackgroundJob",
        "OMDConfigChangeBackgroundJob",
        "BulkDiscoveryBackgroundJob",
        "UserSyncBackgroundJob",
        "ServiceDiscoveryBackgroundJob",
        "CheckmkAutomationBackgroundJob",
        "DiagnosticsDumpBackgroundJob",
        "SearchIndexBackgroundJob",
        "SpecGeneratorBackgroundJob",
        "AutodiscoveryBackgroundJob",
        "QuickSetupStageActionBackgroundJob",
        "QuickSetupActionBackgroundJob",
    ]

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
        expected_jobs += [
            "BakeAgentsBackgroundJob",
            "SignAgentsBackgroundJob",
            "ReportingBackgroundJob",
            "LicensingOnlineVerificationBackgroundJob",
        ]

    assert sorted(job_registry.keys()) == sorted(expected_jobs)


def test_registered_background_jobs_attributes() -> None:
    for job_class in job_registry.values():
        assert isinstance(job_class.job_prefix, str)
        assert isinstance(job_class.gui_title(), str)


@pytest.fixture(autouse=True)
def job_base_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    var_dir = tmp_path

    log_dir = var_dir / "log"
    log_dir.mkdir()

    job_dir = var_dir / "background_jobs"
    job_dir.mkdir()

    # Patch for web.log. Sholdn't we do this for all web tests?
    monkeypatch.setattr(cmk.utils.paths, "log_dir", log_dir)

    monkeypatch.setattr(BackgroundJobDefines, "base_dir", str(job_dir))
    return job_dir


class DummyBackgroundJob(BackgroundJob):
    job_prefix = "dummy_job"

    @classmethod
    def gui_title(cls) -> str:
        return "Dummy Job"

    def __init__(self) -> None:
        self.finish_hello_event = threading.Event()

        super().__init__(self.job_prefix)

    def execute_hello(self, job_interface: BackgroundProcessInterface, args: NoArgs) -> None:
        job_interface.send_progress_update("Hallo :-)")
        self.finish_hello_event.wait()

    def execute_endless(self, job_interface: BackgroundProcessInterface, args: NoArgs) -> None:
        job_interface.send_progress_update("Hanging loop")
        while not job_interface.stop_event.is_set():
            time.sleep(0.1)


@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs")
def test_start_job() -> None:
    job = DummyBackgroundJob()

    status = job.get_status()
    assert status.state == JobStatusStates.INITIALIZED

    assert (
        result := job.start(
            simple_job_target(job.execute_hello),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
            override_job_log_level=logging.DEBUG,
        )
    ).is_ok(), result.error
    wait_until(job.is_active, timeout=10, interval=0.1)

    assert job.start(
        simple_job_target(job.execute_hello),
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    ).is_error()
    assert job.is_active()

    job.finish_hello_event.set()

    wait_until(lambda: not job.is_active(), timeout=10, interval=0.1)

    status = job.get_status()
    assert status.state == JobStatusStates.FINISHED

    output = "\n".join(status.loginfo["JobProgressUpdate"])
    # Make sure we get the generic background job output
    assert "Initialized background job" in output
    # Make sure we get the job specific output
    assert "Hallo :-)" in output


@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs")
def test_stop_job() -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error

    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=10,
        interval=0.1,
    )

    status = job.get_status()
    assert status.state == JobStatusStates.RUNNING

    job.stop()
    wait_until(lambda: not job.is_active(), timeout=10, interval=0.1)

    status = job.get_status()
    assert status.state == JobStatusStates.STOPPED

    output = "\n".join(status.loginfo["JobProgressUpdate"])
    assert "Job was stopped" in output


@pytest.mark.usefixtures("request_context")
def test_job_status_not_started() -> None:
    job = DummyBackgroundJob()
    # Seems the attributes defined for the job, like "deletable" or "title" are not correct in
    # this stage. Looks like this should be changed.
    snapshot = job.get_status_snapshot()
    assert snapshot.has_exception is False
    assert snapshot.acknowledged_by is None
    assert job.is_available() is False
    assert job.is_deletable() is True
    assert job.is_visible() is True
    assert job.may_stop() is False
    assert job.may_delete() is False
    assert job.is_active() is False
    assert job.exists() is False
    assert job.get_job_id() == "dummy_job"
    assert job.get_title() == "Background job"


@pytest.mark.usefixtures("request_context", "allow_background_jobs")
def test_job_status_while_running() -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=10,
        interval=0.1,
    )

    snapshot = job.get_status_snapshot()
    assert snapshot.has_exception is False
    assert snapshot.acknowledged_by is None
    assert job.is_available() is True
    assert job.is_deletable() is False
    assert job.is_visible() is True
    assert job.may_stop() is False
    assert job.may_delete() is False
    assert job.is_active() is True
    assert job.exists() is True
    assert job.get_job_id() == "dummy_job"
    assert job.get_title() == "Dummy Job"
    job.stop()


@pytest.mark.usefixtures("request_context", "allow_background_jobs")
def test_job_status_after_stop() -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=20,
        interval=0.1,
    )
    job.stop()

    status = job.get_status()
    assert status.state == JobStatusStates.STOPPED

    snapshot = job.get_status_snapshot()
    assert snapshot.has_exception is False
    assert snapshot.acknowledged_by is None
    assert job.is_available() is True
    assert job.is_deletable() is False
    assert job.is_visible() is True
    assert job.may_stop() is False
    assert job.may_delete() is False
    assert job.is_active() is False
    assert job.exists() is True
    assert job.get_job_id() == "dummy_job"
    assert job.get_title() == "Dummy Job"


def test_running_job_ids_none() -> None:
    assert not running_job_ids(logging.getLogger())


@pytest.mark.usefixtures("allow_background_jobs")
def test_running_job_ids_one_running() -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=20,
        interval=0.1,
    )

    try:
        assert running_job_ids(logging.getLogger()) == ["dummy_job"]
    finally:
        job.stop()


@pytest.mark.usefixtures("allow_background_jobs")
def test_wait_for_background_jobs_while_one_running_for_too_long(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=20,
        interval=0.1,
    )

    try:
        with caplog.at_level(logging.INFO):
            try:
                job_registry.register(DummyBackgroundJob)
                wait_for_background_jobs(logging.getLogger(), timeout=1)
            finally:
                job_registry.unregister("DummyBackgroundJob")

        logs = [rec.message for rec in caplog.records]
        assert "Waiting for dummy_job to finish..." in logs
        assert "WARNING: Did not finish within 1 seconds" in logs
    finally:
        job.stop()


@pytest.mark.skip("CMK-21655")
@pytest.mark.usefixtures("allow_background_jobs")
def test_wait_for_background_jobs_while_one_running_but_finishes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = DummyBackgroundJob()
    assert (
        result := job.start(
            simple_job_target(job.execute_endless),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=True,
                user=None,
            ),
        )
    ).is_ok(), result.error
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=20,
        interval=0.1,
    )

    with caplog.at_level(logging.INFO):
        try:
            job_registry.register(DummyBackgroundJob)
            threading.Thread(target=job.stop).start()
            wait_for_background_jobs(logging.getLogger(), timeout=2)
        finally:
            job_registry.unregister("DummyBackgroundJob")

    logs = [rec.message for rec in caplog.records]
    assert "Waiting for dummy_job to finish..." in logs
    assert "WARNING: Did not finish within 2 seconds" not in logs


# Works with -pno:opentelemetry but not with the plugin
@pytest.mark.skip(reason="Does not work in all scenarios")
@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs", "reset_global_tracer_provider")
def test_tracing_with_background_job(tmp_path: Path) -> None:
    terminate_signal_file = tmp_path / "terminate_signal"
    exporter = InMemorySpanExporter()

    job = DummyBackgroundJob()

    provider = init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
        extra_resource_attributes={"cmk.ding": "dong"},
        host_name="myhost",
    )
    provider.add_span_processor(BatchSpanProcessor(exporter, export_timeout_millis=3000))

    with tracer.span("test_tracing_with_background_job"):
        status = job.get_status()
        assert status.state == JobStatusStates.INITIALIZED

        assert (
            result := job.start(
                JobTarget(
                    callable=job_callback,
                    args=JobArgs(signal_file=terminate_signal_file),
                ),
                InitialStatusArgs(
                    title=job.gui_title(),
                    deletable=False,
                    stoppable=True,
                    user=None,
                ),
            )
        ).is_ok(), result.error
        wait_until(job.is_active, timeout=20, interval=0.1)
        assert job.is_active()

        terminate_signal_file.touch()
        try:
            wait_until(
                lambda: job.get_status().state
                not in [JobStatusStates.INITIALIZED, JobStatusStates.RUNNING],
                timeout=20,
                interval=0.1,
            )
        except TimeoutError:
            raise

        status = job.get_status()
        output = "\n".join(status.loginfo["JobProgressUpdate"])
        assert status.state == JobStatusStates.FINISHED, output

    provider.force_flush()

    # Check spans produced in the parent process
    span_names = [span.name for span in exporter.spans]
    assert "start_background_job[dummy_job]" in span_names, span_names

    # Check spans produced in the background job
    assert "job_callback" in span_names
    assert "run_process[dummy_job]" in span_names


@pytest.fixture(name="reset_global_tracer_provider")
def _fixture_reset_global_tracer_provider() -> Iterator[None]:
    provider_orig = otel_trace._TRACER_PROVIDER
    try:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False
        otel_trace._TRACER_PROVIDER = None
        yield
    finally:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False
        otel_trace._TRACER_PROVIDER = provider_orig


class JobArgs(BaseModel, frozen=True):
    signal_file: Path


@tracer.instrument("job_callback")
def job_callback(job_interface: BackgroundProcessInterface, args: JobArgs) -> None:
    job_interface.send_progress_update("Hi :-)")
    while not args.signal_file.exists():
        time.sleep(0.05)


class InMemorySpanExporter(SpanExporter):
    """Collects spans in memory and provides for inspection"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            self._spans += spans
        return SpanExportResult.SUCCESS

    @property
    def spans(self) -> list[ReadableSpan]:
        with self._lock:
            return self._spans

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class JobSpanExporter(SpanExporter):
    """Collects span names in the background job directory"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            with self.path.open("a+") as f:
                f.write(str(span.name) + "\n")
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
