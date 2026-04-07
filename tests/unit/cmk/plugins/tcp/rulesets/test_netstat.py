#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.tcp.rulesets.netstat import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"interval": 300},
            {"deployment": ("cached", 300.0)},
            id="old_with_interval",
        ),
        pytest.param({}, {"deployment": ("sync", None)}, id="old_without_interval"),
        pytest.param(
            {"deployment": ("cached", 600.0)},
            {"deployment": ("cached", 600.0)},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
