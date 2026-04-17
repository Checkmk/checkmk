#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.files.rulesets.mk_filestats import migrate


@pytest.mark.parametrize(
    "old_value, expected",
    [
        (
            None,
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"deployment": None, "sections": []},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"deployment": "with_configuration", "sections": []},
            {"deployment": ("sync", None), "sections": []},
        ),
        (
            {"deployment": "plugin_only"},
            {"deployment": ("sync", None), "deploy_config": False},
        ),
        (
            {
                "deployment": ("sync", None),
                "sections": [{"name": "my_group", "input_patterns": "/tmp/*"}],
            },
            {
                "deployment": ("sync", None),
                "sections": [{"name": "my_group", "input_patterns": "/tmp/*"}],
            },
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {
                "deployment": "with_configuration",
                "sections": [
                    {
                        "name": "my_group",
                        "input_patterns": "/tmp/*",
                        "grouping": [
                            ("my_subgroup", ("regex", "/tmp/foo*")),
                        ],
                    }
                ],
            },
            {
                "deployment": ("sync", None),
                "sections": [
                    {
                        "name": "my_group",
                        "input_patterns": "/tmp/*",
                        "grouping": [
                            {"group_name": "my_subgroup", "condition": ("regex", "/tmp/foo*")},
                        ],
                    }
                ],
            },
        ),
        (
            {
                "deployment": "with_configuration",
                "sections": [],
                "DEFAULT": {
                    "grouping": [
                        ("default_subgroup", ("regex", "/var/log/*")),
                    ]
                },
            },
            {
                "deployment": ("sync", None),
                "sections": [],
                "default": {
                    "grouping": [
                        {"group_name": "default_subgroup", "condition": ("regex", "/var/log/*")},
                    ]
                },
            },
        ),
    ],
)
def test_migrate(old_value: object, expected: object) -> None:
    assert migrate(old_value) == expected
