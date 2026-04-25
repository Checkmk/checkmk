#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.mk_filehandler import get_mk_filehandler_files


@pytest.mark.parametrize(
    "conf, expected",
    [
        pytest.param(
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.LINUX, source=Path("mk_filehandler"), interval=None)],
            id="sync",
        ),
        pytest.param(
            {"deployment": ("cached", 3600.0)},
            [Plugin(base_os=OS.LINUX, source=Path("mk_filehandler"), interval=3600)],
            id="cached",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            [],
            id="do_not_deploy",
        ),
    ],
)
def test_mk_filehandler_files(conf: dict[str, object], expected: list[Plugin]) -> None:
    result = list(get_mk_filehandler_files(conf))
    assert result == expected
