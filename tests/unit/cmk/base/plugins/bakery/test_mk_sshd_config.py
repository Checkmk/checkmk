#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.mk_sshd_config import get_mk_sshd_config_files


def test_mk_sshd_config_files_enabled() -> None:
    result = list(get_mk_sshd_config_files({"deployment": ("sync", None)}))
    expected = [Plugin(base_os=OS.LINUX, source=Path("mk_sshd_config"), interval=None)]
    assert result == expected


def test_mk_sshd_config_files_disabled() -> None:
    result = list(get_mk_sshd_config_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
