#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import subprocess
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import pytest
import time_machine

import cmk.utils.paths
from cmk.utils.backup.config import CMASystemConfig, Config, SiteConfig
from cmk.utils.backup.job import JobConfig, JobState
from cmk.utils.backup.targets import TargetId
from cmk.utils.user import UserId

from cmk.gui.backup.handler import Config as BackupConfig
from cmk.gui.backup.handler import Job
from cmk.gui.backup.pages import ModeBackupEditKey
from cmk.gui.logged_in import user

from cmk.crypto.password import Password


@pytest.mark.usefixtures("request_context")
def test_backup_key_create_web(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "id", UserId("dingdöng"))
        store_path = Path(cmk.utils.paths.default_config_dir, "backup_keys.mk")

        assert not store_path.exists()
        mode = ModeBackupEditKey()

        # First create a backup key
        mode._create_key(alias="älias", passphrase=Password("passphra$e"))

        assert store_path.exists()

        # Then test key existence
        test_mode = ModeBackupEditKey()
        keys = test_mode.key_store.load()
        assert len(keys) == 1

        assert store_path.exists()
        store_path.unlink()


@pytest.fixture(name="backup_config")
def fixture_backup_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BackupConfig:
    def fake_run(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    (cmk.utils.paths.omd_root / "etc/cron.d").mkdir(parents=True, exist_ok=True)
    return BackupConfig(
        Config(
            site=SiteConfig(targets={}, jobs={}),
            cma_system=CMASystemConfig(targets={}),
            path_site=tmp_path / "backup.mk",
        )
    )


def _daily_job_config(disabled: bool) -> JobConfig:
    return {
        "title": "My job",
        "encrypt": None,
        "target": TargetId("local"),
        "compress": False,
        "schedule": {"disabled": disabled, "period": "day", "timeofday": [(2, 0)]},
        "no_history": False,
    }


def test_add_job_updates_next_schedule_of_reenabled_job(backup_config: BackupConfig) -> None:
    job = Job("myjob", _daily_job_config(disabled=False))
    state_path = job.state_file_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        JobState(
            state="finished", started=0.0, output="", success=True, next_schedule="disabled"
        ).model_dump_json()
    )

    with time_machine.travel(datetime(2026, 1, 1, 12, 0).astimezone(), tick=False):
        backup_config.add_job(job)

    assert job.state().next_schedule == datetime(2026, 1, 2, 2, 0).timestamp()


def test_add_new_job_creates_no_state_file(backup_config: BackupConfig) -> None:
    job = Job("myjob", _daily_job_config(disabled=False))

    backup_config.add_job(job)

    assert not job.state_file_path().exists()
