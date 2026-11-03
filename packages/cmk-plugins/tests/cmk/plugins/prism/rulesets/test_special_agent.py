#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.prism.rulesets.special_agent import _migrate


@pytest.mark.parametrize(
    "raw_params, migrated_params",
    [
        pytest.param(
            {"username": "user"},
            {
                "username": "user",
                "no_cert_check": False,
                "api_version": "legacy",
            },
            id="pre 2.4 rules get cert check and legacy API",
        ),
        pytest.param(
            {"username": "user", "no_cert_check": True},
            {
                "username": "user",
                "no_cert_check": True,
                "api_version": "legacy",
            },
            id="pre 3.0 rules get legacy API",
        ),
        pytest.param(
            {
                "username": "user",
                "no_cert_check": False,
                "api_version": "v4",
            },
            {
                "username": "user",
                "no_cert_check": False,
                "api_version": "v4",
            },
            id="rules with API version remain unchanged",
        ),
    ],
)
def test_migrate(
    raw_params: Mapping[str, object],
    migrated_params: Mapping[str, object],
) -> None:
    assert _migrate(dict(raw_params)) == migrated_params
