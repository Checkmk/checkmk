#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.mtr import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"interval": 60, "mtr_config": [{"hostname": "example.com"}]},
            {"deployment": ("cached", 60.0), "mtr_config": [{"hostname": "example.com"}]},
            id="old_config",
        ),
        pytest.param(
            {
                "deployment": ("cached", 120.0),
                "mtr_config": [{"hostname": "example.com"}],
            },
            {
                "deployment": ("cached", 120.0),
                "mtr_config": [{"hostname": "example.com"}],
            },
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
