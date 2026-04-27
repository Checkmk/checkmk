#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.mk_apt import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"interval": 0, "method": "upgrade", "update": True},
            {"deployment": ("sync", None), "method": "upgrade", "update": True},
            id="deploy_sync",
        ),
        pytest.param(
            {"interval": 86400, "method": "dist-upgrade", "update": False},
            {"deployment": ("cached", 86400.0), "method": "dist_upgrade", "update": False},
            id="deploy_cached",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("sync", None), "method": "upgrade", "update": True},
            {"deployment": ("sync", None), "method": "upgrade", "update": True},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
