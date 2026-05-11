#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.mailman_lists.bakery.mailman_lists import bakery_plugin_mailman_lists


@pytest.mark.parametrize(
    "conf, expected",
    [
        pytest.param(
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.LINUX, source=Path("mailman3_lists"), interval=None)],
            id="sync",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            [],
            id="do_not_deploy",
        ),
    ],
)
def test_mailman_lists_files(conf: dict[str, object], expected: list[Plugin]) -> None:
    parsed = bakery_plugin_mailman_lists.parameter_parser(conf)
    result = list(bakery_plugin_mailman_lists.files_function(parsed))
    assert result == expected
