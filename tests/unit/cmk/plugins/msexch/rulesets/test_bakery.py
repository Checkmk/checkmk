#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.msexch_dag import migrate as migrate_dag
from cmk.gui.plugins.legacy_bakery_rulesets.msexch_database import migrate as migrate_database


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(True, {"deployment": ("sync", None)}, id="deploy"),
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated",
        ),
    ],
)
def test_migrate_dag(old: object, expected: dict[str, object]) -> None:
    assert migrate_dag(old) == expected


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(True, {"deployment": ("sync", None)}, id="deploy"),
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated",
        ),
    ],
)
def test_migrate_database(old: object, expected: dict[str, object]) -> None:
    assert migrate_database(old) == expected
