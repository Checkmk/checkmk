#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.sap.bakery.mk_saprouter import bakery_plugin_mk_saprouter


@pytest.mark.parametrize(
    "conf, expected",
    [
        pytest.param(
            {"deployment": ("cached", 300.0), "user": "saprouter", "path": "/usr/sap/sapgenpse"},
            [
                Plugin(base_os=OS.LINUX, source=Path("mk_saprouter"), interval=300),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=["SAPROUTER_USER=saprouter", "SAPGENPSE_PATH=/usr/sap/sapgenpse"],
                    target=Path("saprouter.cfg"),
                    include_header=True,
                ),
            ],
            id="cached",
        ),
        pytest.param(
            {"deployment": ("sync", None), "user": "admin", "path": "/opt/sapgenpse"},
            [
                Plugin(base_os=OS.LINUX, source=Path("mk_saprouter"), interval=None),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=["SAPROUTER_USER=admin", "SAPGENPSE_PATH=/opt/sapgenpse"],
                    target=Path("saprouter.cfg"),
                    include_header=True,
                ),
            ],
            id="sync",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            [],
            id="do_not_deploy",
        ),
        pytest.param(
            {
                "deployment": ("sync", None),
                "user": "sap user",
                "path": "/path with spaces/sapgenpse",
            },
            [
                Plugin(base_os=OS.LINUX, source=Path("mk_saprouter"), interval=None),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=[
                        "SAPROUTER_USER='sap user'",
                        "SAPGENPSE_PATH='/path with spaces/sapgenpse'",
                    ],
                    target=Path("saprouter.cfg"),
                    include_header=True,
                ),
            ],
            id="special_chars",
        ),
    ],
)
def test_mk_saprouter_files(conf: dict[str, object], expected: list[Plugin | PluginConfig]) -> None:
    parsed = bakery_plugin_mk_saprouter.parameter_parser(conf)
    result = list(bakery_plugin_mk_saprouter.files_function(parsed))
    assert sorted(result, key=repr) == sorted(expected, key=repr)
