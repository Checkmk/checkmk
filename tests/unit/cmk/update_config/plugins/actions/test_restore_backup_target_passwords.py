#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest

import cmk.update_config.plugins.actions.restore_backup_target_passwords as action_module
from cmk.ccc.store import load_object_from_file, save_object_to_file
from cmk.update_config.lib import ExpiryVersion
from cmk.utils.backup.config import CMASystemConfig, Config, SiteConfig

_LOGGER = logging.getLogger(__name__)


def _patch_config_path(monkeypatch: pytest.MonkeyPatch, backup_mk: Path) -> None:
    def load() -> Config:
        return Config(
            site=SiteConfig.load(backup_mk),
            cma_system=CMASystemConfig(targets={}),
            path_site=backup_mk,
        )

    monkeypatch.setattr(Config, "load", staticmethod(load))


def _run_action() -> None:
    action_module.RestoreBackupTargetPasswords(
        name="restore_backup_target_passwords",
        title="t",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_260,
    )(_LOGGER)


def test_restore_action_rewrites_formspec_secret_to_password_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_mk = tmp_path / "backup.mk"
    save_object_to_file(
        backup_mk,
        {
            "targets": {
                "t1": {
                    "title": "S3",
                    "remote": (
                        "aws_s3_bucket",
                        {
                            "remote": {
                                "access_key": "AKIA",
                                "secret": (
                                    "cmk_postprocessed",
                                    "explicit_password",
                                    ("uuid", "secret"),
                                ),
                                "bucket": "my-bucket",
                            },
                            "temp_folder": {"path": "/tmp", "is_mountpoint": False},
                        },
                    ),
                }
            },
            "jobs": {},
        },
    )
    _patch_config_path(monkeypatch, backup_mk)

    _run_action()

    stored = load_object_from_file(backup_mk, default={})
    assert stored["targets"]["t1"]["remote"][1]["remote"]["secret"] == ("password", "secret")


def test_restore_action_leaves_password_id_config_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_mk = tmp_path / "backup.mk"
    save_object_to_file(
        backup_mk,
        {
            "targets": {
                "t1": {
                    "title": "S3",
                    "remote": (
                        "aws_s3_bucket",
                        {
                            "remote": {
                                "access_key": "AKIA",
                                "secret": ("store", "my-store-id"),
                                "bucket": "my-bucket",
                            },
                            "temp_folder": {"path": "/tmp", "is_mountpoint": False},
                        },
                    ),
                }
            },
            "jobs": {},
        },
    )
    mtime_before = backup_mk.stat().st_mtime_ns
    _patch_config_path(monkeypatch, backup_mk)

    _run_action()

    assert backup_mk.stat().st_mtime_ns == mtime_before
