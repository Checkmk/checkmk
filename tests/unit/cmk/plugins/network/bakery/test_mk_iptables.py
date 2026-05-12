#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.network.bakery.mk_iptables import bakery_plugin_mk_iptables


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.LINUX, source=Path("mk_iptables"), interval=None)],
        ),
        (
            {"deployment": ("cached", 3600.0)},
            [Plugin(base_os=OS.LINUX, source=Path("mk_iptables"), interval=3600.0)],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_mk_iptables_files(
    conf: dict[str, object],
    expected_files: list[Plugin],
) -> None:
    parsed = bakery_plugin_mk_iptables.parameter_parser(conf)
    result = list(bakery_plugin_mk_iptables.files_function(parsed))
    assert result == expected_files
