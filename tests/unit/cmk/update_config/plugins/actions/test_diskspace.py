#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger
from pathlib import Path

import pytest

from cmk.diskspace.config import Config, DEFAULT_CONFIG, read_config
from cmk.update_config.plugins.actions import diskspace

DISKSPACE_CONF_01 = ""
DISKSPACE_CONF_02 = """cleanup_abandoned_host_files = 2592000
max_file_age = 31536000
min_file_age = 2592000
min_free_bytes = 10"""
DISKSPACE_CONF_03 = """cleanup_abandoned_host_files = None"""
DISKSPACE_CONF_04 = "cleanup_abandoned_host_files = 2592000"
DISKSPACE_CONF_05 = """min_free_bytes = False
min_file_age = False"""


@pytest.mark.parametrize(
    "old, expected",
    [
        (
            DISKSPACE_CONF_01,
            DEFAULT_CONFIG,
        ),
        (
            DISKSPACE_CONF_02,
            Config(
                max_file_age=31536000,
                min_free_bytes=(10, 2592000),
                cleanup_abandoned_host_files=2592000,
            ),
        ),
        (
            DISKSPACE_CONF_03,
            Config(cleanup_abandoned_host_files=None),
        ),
        (
            DISKSPACE_CONF_04,
            DEFAULT_CONFIG,
        ),
        (
            DISKSPACE_CONF_05,
            Config(min_free_bytes=(0, 0), cleanup_abandoned_host_files=2592000),
        ),
    ],
)
def test_migrate_diskspace(old: str, expected: Config, tmp_path: Path) -> None:
    old_diskspace_conf = tmp_path.joinpath("diskspace.conf")
    old_diskspace_conf.write_text(old)
    diskspace.migrate(old_diskspace_conf, tmp_path, getLogger())
    assert read_config(tmp_path) == expected
