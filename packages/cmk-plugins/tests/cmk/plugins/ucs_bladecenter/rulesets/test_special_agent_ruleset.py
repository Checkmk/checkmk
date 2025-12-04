#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ucs_bladecenter.rulesets.special_agent import migrate_cert_check


@pytest.mark.parametrize(
    "old_params, new_params",
    [
        pytest.param(
            {"username": "passed-through-1", "password": "passed-through-2"},
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "certificate_validation": True,
            },
            id="add mandatory certificate_validation",
        ),
        pytest.param(
            {"username": "passed-through-1", "password": "passed-through-2", "no-cert-check": True},
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "certificate_validation": False,
            },
            id="respect previous setting True",
        ),
        pytest.param(
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "no-cert-check": False,
            },
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "certificate_validation": True,
            },
            id="respect previous setting False",
        ),
        pytest.param(
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "no-cert-check": False,
                "certificate_validation": True,
            },
            {
                "username": "passed-through-1",
                "password": "passed-through-2",
                "certificate_validation": True,
            },
            id="tolerate broken config with both keys (not tolerated by SSC plugin)",
        ),
    ],
)
def test_special_agent_ucs_bladecenter_command_creation(
    old_params: Mapping[str, object],
    new_params: Mapping[str, object],
) -> None:
    assert migrate_cert_check(old_params) == new_params
    assert migrate_cert_check(new_params) == new_params  # idempotency
