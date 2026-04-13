#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.smart.rulesets.bakery import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            "smart_posix",
            {"deployment": ("sync", None)},
            id="deploy_smart_posix",
        ),
        pytest.param(
            "smart",
            {"deployment": ("sync", None), "use_legacy_plugin": True},
            id="deploy_smart_legacy",
        ),
        pytest.param(
            True,
            {"deployment": ("sync", None), "use_legacy_plugin": True},
            id="old_true_becomes_smart_legacy",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("smart_posix", None)},
            {"deployment": ("sync", None)},
            id="old_intermediate_smart_posix",
        ),
        pytest.param(
            {"deployment": ("smart", None)},
            {"deployment": ("sync", None), "use_legacy_plugin": True},
            id="old_intermediate_smart",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
            id="already_migrated_do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated_sync",
        ),
        pytest.param(
            {"deployment": ("sync", None), "use_legacy_plugin": True},
            {"deployment": ("sync", None), "use_legacy_plugin": True},
            id="already_migrated_sync_legacy",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
