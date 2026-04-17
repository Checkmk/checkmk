#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.crypto.password import Password
from cmk.gui.backup.handler import BackupConfig, ModeEditBackupJob
from cmk.gui.backup.pages import ModeBackupEditKey
from cmk.gui.logged_in import user
from cmk.utils.backup.config import CMASystemConfig, Config, SiteConfig
from cmk.utils.backup.targets import TargetId
from cmk.utils.backup.targets.config import LocalTargetConfig, TargetConfig


@pytest.mark.usefixtures("request_context")
def test_backup_key_create_web(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "id", UserId("dingdöng"))
        store_path = cmk.utils.paths.default_config_dir / "backup_keys.mk"

        assert not store_path.exists()
        mode = ModeBackupEditKey()

        # First create a backup key
        mode._create_key(
            alias="älias", passphrase=Password("passphra$e"), use_git=False, default_key_size=1024
        )

        assert store_path.exists()

        # Then test key existence
        test_mode = ModeBackupEditKey()
        keys = test_mode.key_store.load()
        assert len(keys) == 1

        assert store_path.exists()
        store_path.unlink()


def test_backup_target_choices_with_hyphenated_ident(tmp_path: Path) -> None:
    """Regression test for CMK-32749: backup target IDs with hyphens must not raise ValueError.

    Before the fix, SingleChoiceElement validated that 'name' was a valid Python identifier,
    causing a crash when editing jobs whose target ident contained a hyphen (e.g. 'backup-local').
    """
    remote: LocalTargetConfig = ("local", {"path": "foo", "is_mountpoint": False})
    target_config: TargetConfig = {
        "title": "Local backup",
        "remote": remote,
    }
    raw_config = Config(
        site=SiteConfig(
            targets={TargetId("backup-local"): target_config},
            jobs={},
        ),
        cma_system=CMASystemConfig(targets={}),
        path_site=tmp_path / "backup.mk",
    )
    backup_config = BackupConfig(raw_config)

    # Must not raise ValueError
    choices = ModeEditBackupJob.backup_target_choices(backup_config)

    assert len(choices) == 1
    assert choices[0].name == "backup-local"
