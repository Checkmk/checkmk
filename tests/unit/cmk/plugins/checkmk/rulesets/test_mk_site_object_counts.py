#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.checkmk.rulesets.mk_site_object_counts import migrate


@pytest.mark.parametrize(
    "old_value, expected",
    [
        (
            None,
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {},
            {"deployment": ("sync", None)},
        ),
        (
            {"tags": ["prod", "test"]},
            {"deployment": ("sync", None), "tags": ["prod", "test"]},
        ),
        (
            {"service_check_commands": ["check_mk"]},
            {"deployment": ("sync", None), "service_check_commands": ["check_mk"]},
        ),
        (
            {
                "tags": ["prod"],
                "sites": [("site1", ["tag1"], ["cmd1"])],
            },
            {
                "deployment": ("sync", None),
                "tags": ["prod"],
                "sites": [
                    {"site_name": "site1", "tags": ["tag1"], "service_check_commands": ["cmd1"]}
                ],
            },
        ),
        (
            {"deployment": ("sync", None), "tags": ["prod"]},
            {"deployment": ("sync", None), "tags": ["prod"]},
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"deployment": ("cached", 3600.0)},
            {"deployment": ("cached", 3600.0)},
        ),
    ],
)
def test_migrate(old_value: object, expected: object) -> None:
    assert migrate(old_value) == expected


def test_migrate_invalid_value() -> None:
    with pytest.raises(ValueError):
        migrate("unexpected_string")
