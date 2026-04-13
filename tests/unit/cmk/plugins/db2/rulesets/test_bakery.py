#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.db2_mem import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            True,
            {"deployment": ("sync", None)},
            id="deploy_true",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated_sync",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
            id="already_migrated_do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("cached", 3600.0)},
            {"deployment": ("cached", 3600.0)},
            id="already_migrated_cached",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
