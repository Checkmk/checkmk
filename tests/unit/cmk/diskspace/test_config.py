#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.diskspace.config import Config, DEFAULT_CONFIG, read_config

# etc/check_mk/diskspace.d/wato/
NON_DEFAULT_OPTIONS = """# Created by WATO

diskspace_cleanup = {'max_file_age': 31536000, 'min_free_bytes': (50, 2592000)}"""
DEFAULT_FILE = """# Created by WATO

"""

ALL_OPTIONS_UNSET = """# Created by WATO

diskspace_cleanup = {}
"""


def test_read_config_default(tmp_path: Path) -> None:
    wato = tmp_path.joinpath("wato")
    wato.mkdir()
    (wato / "global.mk").write_text(DEFAULT_FILE)
    assert read_config(wato) == DEFAULT_CONFIG


def test_read_config_global_settings(tmp_path: Path) -> None:
    wato = tmp_path.joinpath("wato")
    wato.mkdir()
    (wato / "global.mk").write_text(NON_DEFAULT_OPTIONS)
    assert read_config(wato) == Config(
        max_file_age=31536000, min_free_bytes=(50, 2592000), cleanup_abandoned_host_files=None
    )


def test_read_config_sitespecific(tmp_path: Path) -> None:
    wato = tmp_path.joinpath("wato")
    wato.mkdir()
    (wato / "global.mk").write_text(NON_DEFAULT_OPTIONS)
    (wato / "sitespecific.mk").write_text(ALL_OPTIONS_UNSET)
    assert read_config(wato) == Config(
        max_file_age=None, min_free_bytes=None, cleanup_abandoned_host_files=None
    )
