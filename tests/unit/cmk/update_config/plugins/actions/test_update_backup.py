#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger
from pathlib import Path

from cmk.utils.backup.config import CMASystemConfig, Config, SiteConfig
from cmk.utils.backup.targets import TargetId
from cmk.utils.backup.targets.local import LocalTargetParams
from cmk.utils.paths import default_config_dir

from cmk.update_config.plugins.actions.backup import UpdateBackupConfig


def test_update_backup_config() -> None:
    Config(
        site=SiteConfig.construct(
            targets={
                TargetId("t1"): {
                    "title": "Target1",
                    "remote": (
                        "local",
                        LocalTargetParams(
                            path="/tmp/heute_backup",
                            is_mountpoint=False,
                        ),
                    ),
                }
            },
            jobs={
                "job1": {
                    "title": "Job",
                    "target": TargetId("t1"),
                    "schedule": {
                        "disabled": False,
                        "period": ("week", 2),
                        "timeofday": [
                            (0, 0),
                            None,  # type: ignore[list-item]
                        ],
                    },
                    "compress": False,
                    "encrypt": None,
                    "no_history": False,
                }
            },
        ),
        cma_system=CMASystemConfig(targets={}),
        path_site=Path(default_config_dir) / "backup.mk",
    ).save()

    UpdateBackupConfig(
        name="update_backup_config",
        title="Update backup config",
        sort_index=110,
    )(getLogger(), {})

    assert dict(Config.load().site) == {
        "targets": {
            "t1": {
                "title": "Target1",
                "remote": ("local", {"path": "/tmp/heute_backup", "is_mountpoint": False}),
            }
        },
        "jobs": {
            "job1": {
                "title": "Job",
                "target": "t1",
                "schedule": {
                    "disabled": False,
                    "period": ("week", 2),
                    "timeofday": [
                        (0, 0),
                    ],
                },
                "compress": False,
                "encrypt": None,
                "no_history": False,
            }
        },
    }
