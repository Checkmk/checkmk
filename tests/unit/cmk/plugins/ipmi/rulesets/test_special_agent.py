#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ipmi_sensors.rulesets.special_agent import _migrate
from cmk.server_side_calls.v1._utils import Secret


@pytest.mark.parametrize(
    "raw_params, migrated_params",
    [
        pytest.param(
            {
                "username": "user",
                "password": Secret(23),
                "privilege_lvl": "user",
            },
            {
                "username": "user",
                "password": Secret(23),
                "privilege_lvl": "user",
                "cipher_suite_id": "suite_3",
            },
            id="old rules get suite_3 as cipher_suite_id",
        ),
        pytest.param(
            {
                "username": "admin",
                "password": Secret(42),
                "privilege_lvl": "admin",
                "cipher_suite_id": "suite_17",
            },
            {
                "username": "admin",
                "password": Secret(42),
                "privilege_lvl": "admin",
                "cipher_suite_id": "suite_17",
            },
            id="rules with cipher_suite_id remain unchanged",
        ),
    ],
)
def test_migrate(
    raw_params: Mapping[str, object],
    migrated_params: Mapping[str, object],
) -> None:
    assert _migrate(raw_params) == migrated_params
