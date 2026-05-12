#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.firewall import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"mode": "configure", "port": "auto"},
            {"mode": "configure", "port": "auto"},
            id="already_migrated_configure_auto",
        ),
        pytest.param(
            {"mode": "none", "port": "all"},
            {"mode": "none", "port": "all"},
            id="already_migrated_none_all",
        ),
        pytest.param(
            {"mode": "remove", "port": "auto"},
            {"mode": "remove", "port": "auto"},
            id="already_migrated_remove",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
