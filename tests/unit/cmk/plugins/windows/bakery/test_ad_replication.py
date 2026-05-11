#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.windows.bakery.ad_replication import bakery_plugin_ad_replication


@pytest.mark.parametrize(
    "conf, expected",
    [
        pytest.param(
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.WINDOWS, source=Path("ad_replication.bat"), interval=None)],
            id="sync",
        ),
        pytest.param(
            {"deployment": ("cached", 3600.0)},
            [Plugin(base_os=OS.WINDOWS, source=Path("ad_replication.bat"), interval=3600)],
            id="cached",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            [],
            id="do_not_deploy",
        ),
    ],
)
def test_ad_replication_files(conf: dict[str, object], expected: list[Plugin]) -> None:
    parsed = bakery_plugin_ad_replication.parameter_parser(conf)
    result = list(bakery_plugin_ad_replication.files_function(parsed))
    assert result == expected
