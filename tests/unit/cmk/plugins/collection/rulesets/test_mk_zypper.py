#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.mk_zypper import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            14400,
            {"deployment": ("cached", 14400.0)},
            id="deploy_cached",
        ),
        pytest.param(
            0,
            {"deployment": ("sync", None)},
            id="deploy_sync",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("cached", 14400.0)},
            {"deployment": ("cached", 14400.0)},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
