#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger

from cmk.gui.backup import Config, site_config_path

from cmk.update_config.plugins.actions.backup import UpdateBackupConfig


def test_update_backup_config() -> None:
    Config(site_config_path()).save(
        {
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
                            None,
                        ],
                    },
                    "compress": False,
                    "encrypt": None,
                    "no_history": False,
                }
            },
        }
    )

    UpdateBackupConfig(
        name="update_backup_config",
        title="Update backup config",
        sort_index=110,
    )(getLogger(), {})

    assert Config(site_config_path()).load() == {
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
