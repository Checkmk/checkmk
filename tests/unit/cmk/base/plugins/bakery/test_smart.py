#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.smart import get_smart_files


def test_smart_files_smart_posix_sync() -> None:
    result = list(get_smart_files({"deployment": ("sync", None)}))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("smart_posix"), interval=None),
    ]
    assert result == expected


def test_smart_files_smart_legacy_sync() -> None:
    result = list(get_smart_files({"deployment": ("sync", None), "use_legacy_plugin": True}))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("smart"), interval=None),
    ]
    assert result == expected


def test_smart_files_smart_posix_cached() -> None:
    result = list(get_smart_files({"deployment": ("cached", 3600.0)}))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("smart_posix"), interval=3600),
    ]
    assert result == expected


def test_smart_files_do_not_deploy() -> None:
    result = list(get_smart_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
