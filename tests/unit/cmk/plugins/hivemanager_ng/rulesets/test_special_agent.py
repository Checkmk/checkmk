#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.hivemanager_ng.rulesets.special_agent import _migrate


@pytest.mark.parametrize(
    "raw_params, migrated_params",
    [
        pytest.param(
            {
                "url": "https://cloud.aerohive.com",
                "vhm_id": "102",
                "api_token": "token",
                "client_id": "clientID",
                "client_secret": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid", "secret"),
                ),
                "redirect_url": "https://redirect.com",
            },
            {"url": "https://cloud.aerohive.com"},
            id="legacy rule keeps only the URL; credentials must be re-entered",
        ),
        pytest.param(
            {
                "url": "https://api.extremecloudiq.com",
                "username": "user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid", "secret"),
                ),
            },
            {
                "url": "https://api.extremecloudiq.com",
                "username": "user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid", "secret"),
                ),
            },
            id="already migrated rule remains unchanged",
        ),
    ],
)
def test_migrate(
    raw_params: Mapping[str, object],
    migrated_params: Mapping[str, object],
) -> None:
    assert _migrate(raw_params) == migrated_params
