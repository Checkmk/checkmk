#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.plesk import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(3600, {"deployment": ("cached", 3600.0)}, id="deploy_with_interval"),
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated_sync",
        ),
        pytest.param(
            {"deployment": ("cached", 600.0)},
            {"deployment": ("cached", 600.0)},
            id="already_migrated_cached",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
