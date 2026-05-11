#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.files.bakery.mk_filestats import bakery_plugin_mk_filestats

_CONFIG_LINES = [
    "[DEFAULT]",
    "subgroups_delimiter: @@",
    "",
    "[my_file_group]",
    "input_patterns: /home/mydir/*",
    "",
    "[my_file_group@@my_file_subgroup]",
    "grouping_regex: /home/mydir/banana*",
    "",
]


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            {
                "deployment": ("sync", None),
                "sections": [
                    {
                        "name": "my_file_group",
                        "input_patterns": "/home/mydir/*",
                        "grouping": [
                            {
                                "group_name": "my_file_subgroup",
                                "condition": ("regex", "/home/mydir/banana*"),
                            }
                        ],
                    }
                ],
                "subgroups_delimiter": "@@",
            },
            [
                Plugin(
                    base_os=OS.LINUX,
                    source=Path("mk_filestats.py"),
                    interval=None,
                ),
                Plugin(
                    base_os=OS.SOLARIS,
                    source=Path("mk_filestats.py"),
                    interval=None,
                ),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=_CONFIG_LINES,
                    target=Path("filestats.cfg"),
                    include_header=True,
                ),
                PluginConfig(
                    base_os=OS.SOLARIS,
                    lines=_CONFIG_LINES,
                    target=Path("filestats.cfg"),
                    include_header=True,
                ),
            ],
        ),
        (
            {"deployment": ("sync", None), "deploy_config": False},
            [
                Plugin(
                    base_os=OS.LINUX,
                    source=Path("mk_filestats.py"),
                    interval=None,
                ),
                Plugin(
                    base_os=OS.SOLARIS,
                    source=Path("mk_filestats.py"),
                    interval=None,
                ),
            ],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_mk_filestats_files(
    conf: dict[str, object],
    expected_files: list[Plugin | PluginConfig],
) -> None:
    parsed = bakery_plugin_mk_filestats.parameter_parser(conf)
    result = list(bakery_plugin_mk_filestats.files_function(parsed))
    assert result == expected_files
