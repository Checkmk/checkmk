#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.ssh.bakery.mk_sshd_config import bakery_plugin_mk_sshd_config


@pytest.mark.parametrize(
    "conf, expected",
    [
        pytest.param(
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.LINUX, source=Path("mk_sshd_config"), interval=None)],
            id="sync",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            [],
            id="do_not_deploy",
        ),
    ],
)
def test_mk_sshd_config_files(conf: dict[str, object], expected: list[Plugin]) -> None:
    parsed = bakery_plugin_mk_sshd_config.parameter_parser(conf)
    result = list(bakery_plugin_mk_sshd_config.files_function(parsed))
    assert result == expected
