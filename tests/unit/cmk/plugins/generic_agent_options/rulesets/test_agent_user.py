#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.generic_agent_options.rulesets.agent_user import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            "legacyuser",
            {"user": "legacyuser"},
            id="plain_string",
        ),
        pytest.param(
            {"user": "legacyuser"},
            {"user": "legacyuser"},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
