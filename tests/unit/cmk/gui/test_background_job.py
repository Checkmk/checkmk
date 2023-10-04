#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import sys
import time

import pytest

import tests.testlib as testlib

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.log
from cmk.gui import config
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundJobDefines,
    InitialStatusArgs,
    job_registry,
    JobStatusStates,
)


@pytest.fixture(autouse=True)
def debug_logging(load_config):
    cmk.gui.log.set_log_levels(
        {"cmk.web": logging.DEBUG, "cmk.web.background-job": cmk.utils.log.VERBOSE}
    )
    yield
    cmk.gui.log.set_log_levels(config.active_config.log_levels)


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
        "DiscoveredHostLabelSyncJob",
        "SyncRemoteSitesBackgroundJob",
        "HostRemovalBackgroundJob",
        "AutodiscoveryBackgroundJob",
    ]

    if cmk_version.edition() is not cmk_version.Edition.CRE:
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
    def gui_title(cls):
        return "Dummy Job"

    def __init__(self) -> None:
        self.finish_hello_event = multiprocessing.Event()

        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                deletable=False,
                stoppable=True,
            ),
        )

    def execute_hello(self, job_interface):
        sys.stdout.write("Hallo :-)\n")
        sys.stdout.flush()
        self.finish_hello_event.wait()

    def execute_endless(self, job_interface):
        sys.stdout.write("Hanging loop\n")
        sys.stdout.flush()
        time.sleep(100)


@pytest.mark.usefixtures("request_context")
def test_start_job() -> None:
    job = DummyBackgroundJob()

    status = job.get_status()
    assert status.state == JobStatusStates.INITIALIZED

    job.start(job.execute_hello)
    testlib.wait_until(job.is_active, timeout=5, interval=0.1)

    with pytest.raises(BackgroundJobAlreadyRunning):
        job.start(job.execute_hello)
    assert job.is_active()

    job.finish_hello_event.set()

    testlib.wait_until(
        lambda: job.get_status().state
        not in [JobStatusStates.INITIALIZED, JobStatusStates.RUNNING],
        timeout=5,
        interval=0.1,
    )

    status = job.get_status()
    assert status.state == JobStatusStates.FINISHED

    output = "\n".join(status.loginfo["JobProgressUpdate"])
    assert "Initialized background job" in output
    assert "Hallo :-)" in output


@pytest.mark.usefixtures("request_context")
def test_stop_job() -> None:
    job = DummyBackgroundJob()
    job.start(job.execute_endless)

    testlib.wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=5,
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


@pytest.mark.usefixtures("request_context")
def test_job_status_while_running() -> None:
    job = DummyBackgroundJob()
    job.start(job.execute_endless)
    testlib.wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=5,
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


@pytest.mark.usefixtures("request_context")
def test_job_status_after_stop() -> None:
    job = DummyBackgroundJob()
    job.start(job.execute_endless)
    testlib.wait_until(
        lambda: "Hanging loop" in job.get_status().loginfo["JobProgressUpdate"],
        timeout=5,
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
