#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.mk_zypper import get_mk_zypper_files


def test_mk_zypper_files_sync() -> None:
    result = list(get_mk_zypper_files({"deployment": ("sync", None)}))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("mk_zypper"), interval=None),
    ]
    assert result == expected


def test_mk_zypper_files_cached() -> None:
    result = list(get_mk_zypper_files({"deployment": ("cached", 300.0)}))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("mk_zypper"), interval=300),
    ]
    assert result == expected


def test_mk_zypper_files_do_not_deploy() -> None:
    result = list(get_mk_zypper_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
