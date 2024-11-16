#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import sys
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from functools import partial
from multiprocessing.synchronize import Event
from pathlib import Path

import pytest
from opentelemetry import trace as otel_trace

from tests.testlib.utils import wait_until

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
    running_job_ids,
    wait_for_background_jobs,
)

from cmk.trace import get_tracer, init_tracing, ReadableSpan, TracerProvider
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
        "UserProfileCleanupBackgroundJob",
        "ServiceDiscoveryBackgroundJob",
        "ActivationCleanupBackgroundJob",
        "CheckmkAutomationBackgroundJob",
        "DiagnosticsDumpBackgroundJob",
        "SearchIndexBackgroundJob",
        "SpecGeneratorBackgroundJob",
        "DiscoveredHostLabelSyncJob",
        "SyncRemoteSitesBackgroundJob",
        "HostRemovalBackgroundJob",
        "AutodiscoveryBackgroundJob",
    ]

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
        expected_jobs += [
            "HostRegistrationBackgroundJob",
            "DiscoverRegisteredHostsBackgroundJob",
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
def job_base_dir(tmp_path, monkeypatch):
    var_dir = tmp_path

    log_dir = var_dir / "log"
    log_dir.mkdir()

    job_dir = var_dir / "background_jobs"
    job_dir.mkdir()

    # Patch for web.log. Sholdn't we do this for all web tests?
    monkeypatch.setattr(cmk.utils.paths, "log_dir", str(log_dir))

    monkeypatch.setattr(BackgroundJobDefines, "base_dir", str(job_dir))
    return job_dir


class DummyBackgroundJob(BackgroundJob):
    job_prefix = "dummy_job"

    @classmethod
    def gui_title(cls) -> str:
        return "Dummy Job"

    def __init__(self) -> None:
        self.finish_hello_event = multiprocessing.get_context("spawn").Event()

        super().__init__(self.job_prefix)

    def execute_hello(self, job_interface: BackgroundProcessInterface) -> None:
        sys.stdout.write("Hallo :-)\n")
        sys.stdout.flush()
        self.finish_hello_event.wait()

    def execute_endless(self, job_interface: BackgroundProcessInterface) -> None:
        sys.stdout.write("Hanging loop\n")
        sys.stdout.flush()
        time.sleep(100)


@pytest.mark.skip(reason="Fails randomly: see CMK-18161")
def test_start_job() -> None:
    job = DummyBackgroundJob()

    status = job.get_status()
    assert status.state == JobStatusStates.INITIALIZED

    job.start(
        job.execute_hello,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
        override_job_log_level=logging.DEBUG,
    )
    wait_until(job.is_active, timeout=10, interval=0.1)

    assert job.start(
        job.execute_hello,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    ).is_error()
    assert job.is_active()

    job.finish_hello_event.set()

    wait_until(
        lambda: job.get_status().state
        not in [JobStatusStates.INITIALIZED, JobStatusStates.RUNNING],
        timeout=10,
        interval=0.1,
    )

    status = job.get_status()
    assert status.state == JobStatusStates.FINISHED

    output = "\n".join(status.loginfo["JobProgressUpdate"])
    # Make sure we get the generic background job output
    assert "Initialized background job" in output
    # Make sure we get the job specific output
    assert "Hallo :-)" in output


@pytest.mark.skip(reason="Fails randomly: see CMK-18161")
def test_stop_job() -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )

    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=10,
        interval=0.1,
    )

    status = job.get_status()
    assert status.state == JobStatusStates.RUNNING

    job.stop()

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


@pytest.mark.skip(reason="Fails randomly: see CMK-18161")
@pytest.mark.usefixtures("request_context")
def test_job_status_while_running() -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )
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


@pytest.mark.skip(reason="Fails randomly: see CMK-18161")
@pytest.mark.usefixtures("request_context")
def test_job_status_after_stop() -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )
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


@pytest.mark.skip(reason="Takes too long: see CMK-18161")
def test_running_job_ids_one_running() -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )
    wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=20,
        interval=0.1,
    )

    try:
        assert running_job_ids(logging.getLogger()) == ["dummy_job"]
    finally:
        job.stop()


@pytest.mark.skip(reason="Takes too long: see CMK-18161")
def test_wait_for_background_jobs_while_one_running_for_too_long(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )
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


@pytest.mark.skip(reason="Takes too long: see CMK-18161")
def test_wait_for_background_jobs_while_one_running_but_finishes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = DummyBackgroundJob()
    job.start(
        job.execute_endless,
        InitialStatusArgs(
            title=job.gui_title(),
            deletable=False,
            stoppable=True,
            user=None,
        ),
    )
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


@contextmanager
def _reset_global_fixture_provider() -> Iterator[None]:
    # pylint: disable=protected-access
    provider_orig = otel_trace._TRACER_PROVIDER
    try:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False
        otel_trace._TRACER_PROVIDER = None
        yield
    finally:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = True
        otel_trace._TRACER_PROVIDER = provider_orig


@pytest.mark.skip(reason="Takes too long: see CMK-18161")
@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs")
def test_tracing_with_background_job(tmp_path: Path) -> None:
    exporter = InMemorySpanExporter()

    job = DummyBackgroundJob()
    span_name_path = Path(job.get_work_dir()) / "span_names"

    with _reset_global_fixture_provider():
        provider = init_tracing("test", "background-job")
        provider.add_span_processor(BatchSpanProcessor(exporter))

        with tracer.start_as_current_span("test_tracing_with_background_job"):
            status = job.get_status()
            assert status.state == JobStatusStates.INITIALIZED

            job.start(
                partial(job_callback, job.finish_hello_event),
                InitialStatusArgs(
                    title=job.gui_title(),
                    deletable=False,
                    stoppable=True,
                    user=None,
                ),
                init_span_processor_callback=partial(init_span_processor_callback, span_name_path),
            )
            wait_until(job.is_active, timeout=20, interval=0.1)
            assert job.is_active()

            job.finish_hello_event.set()
            try:
                wait_until(
                    lambda: job.get_status().state
                    not in [JobStatusStates.INITIALIZED, JobStatusStates.RUNNING],
                    timeout=20,
                    interval=0.1,
                )
            except TimeoutError:
                print(job.get_status())
                raise

            status = job.get_status()
            output = "\n".join(status.loginfo["JobProgressUpdate"])
            assert status.state == JobStatusStates.FINISHED, output

            provider.force_flush()

    # Check spans produced in the parent process
    span_names = [span.name for span in exporter.spans]
    assert "start_background_job[dummy_job]" in span_names

    # Check spans produced in the background job
    job_span_names = span_name_path.open().readlines()
    assert "job_callback\n" in job_span_names
    assert "run_process[dummy_job]\n" in job_span_names


def init_span_processor_callback(
    span_name_path: Path, provider: TracerProvider, exporter: SpanExporter | None
) -> None:
    provider.add_span_processor(BatchSpanProcessor(JobSpanExporter(span_name_path)))


@tracer.start_as_current_span("job_callback")
def job_callback(finish_hello_event: Event, job_interface: BackgroundProcessInterface) -> None:
    sys.stdout.write("Hi :-)\n")
    sys.stdout.flush()
    finish_hello_event.wait()


class InMemorySpanExporter(SpanExporter):
    """Collects spans in memory and provides for inspection"""

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans += spans
        return SpanExportResult.SUCCESS

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
