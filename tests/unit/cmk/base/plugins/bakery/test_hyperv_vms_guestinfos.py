#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.hyperv_vms_guestinfos import get_hyperv_vms_guestinfos_files


def test_hyperv_vms_guestinfos_files_sync() -> None:
    result = list(get_hyperv_vms_guestinfos_files({"deployment": ("sync", None)}))
    expected = [Plugin(base_os=OS.WINDOWS, source=Path("hyperv_vms_guestinfos.ps1"), interval=None)]
    assert result == expected


def test_hyperv_vms_guestinfos_files_cached() -> None:
    result = list(get_hyperv_vms_guestinfos_files({"deployment": ("cached", 3600.0)}))
    expected = [Plugin(base_os=OS.WINDOWS, source=Path("hyperv_vms_guestinfos.ps1"), interval=3600)]
    assert result == expected


def test_hyperv_vms_guestinfos_files_do_not_deploy() -> None:
    result = list(get_hyperv_vms_guestinfos_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
