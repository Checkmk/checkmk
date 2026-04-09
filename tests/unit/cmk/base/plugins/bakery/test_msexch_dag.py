#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.msexch_dag import get_msexch_files


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.WINDOWS, source=Path("msexch_dag.ps1"), interval=None)],
        ),
        (
            {"deployment": ("cached", 3600.0)},
            [Plugin(base_os=OS.WINDOWS, source=Path("msexch_dag.ps1"), interval=3600)],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_msexch_dag_files(
    conf: dict[str, object],
    expected_files: list[Plugin],
) -> None:
    result = list(get_msexch_files(conf))
    assert result == expected_files
