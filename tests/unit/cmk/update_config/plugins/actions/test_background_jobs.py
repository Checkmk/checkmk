#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.gui.background_job import BackgroundJobDefines

from cmk.update_config.plugins.actions.background_jobs import (
    JobStatusStore,
    migrate_job_status_spec,
    update_job_status,
    UpdateBackgroundJobStatusSpec,
)


@pytest.fixture(name="plugin", scope="module")
def fixture_plugin() -> UpdateBackgroundJobStatusSpec:
    return UpdateBackgroundJobStatusSpec(
        name="background_job_status_specs",
        title="Background jobs",
        sort_index=60,
    )


def test_cleanup_nothing_to_be_done(plugin: UpdateBackgroundJobStatusSpec) -> None:
    plugin(logging.getLogger(), {})


def test_migrate_job_status_spec_add_missing_mandatory_fields() -> None:
    clean_state = migrate_job_status_spec({}, jobstatus_ctime=12.3)
    assert clean_state == {
        "is_active": True,
        "loginfo": {"JobException": [], "JobProgressUpdate": [], "JobResult": []},
        "pid": None,
        "started": 12.3,
        "state": "initialized",
    }


def test_update_job_status_cleanup_empty_dict_job(tmp_path: Path) -> None:
    job_status = tmp_path / "job1" / BackgroundJobDefines.jobstatus_filename
    job_status.parent.mkdir(parents=True)
    job_status.write_text(repr({}))
    assert job_status.exists()

    update_job_status(logging.getLogger(), job_status.parent)
    assert not job_status.exists()


def test_update_job_status_cleanup_empty_file(tmp_path: Path) -> None:
    job_status = tmp_path / "job1" / BackgroundJobDefines.jobstatus_filename
    job_status.parent.mkdir(parents=True)
    job_status.touch()
    assert job_status.exists()

    update_job_status(logging.getLogger(), job_status.parent)
    assert not job_status.exists()


def test_update_job_status_add_missing_pid(tmp_path: Path) -> None:
    job_status = tmp_path / "job1" / BackgroundJobDefines.jobstatus_filename
    job_status.parent.mkdir(parents=True)
    job_status.touch()
    job_status.write_text(
        repr(
            {
                "is_active": True,
                "loginfo": {"JobException": [], "JobProgressUpdate": [], "JobResult": []},
                "started": 12.3,
                "state": "initialized",
            }
        )
    )

    update_job_status(logging.getLogger(), job_status.parent)
    assert JobStatusStore(str(job_status.parent)).read().pid is None
