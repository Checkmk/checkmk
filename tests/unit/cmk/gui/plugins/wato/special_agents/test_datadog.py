#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.special_agents.datadog import (
    migrate_password_back,
    migrate_password_forth,
    migrate_proxy_forth,
)


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            (("password", "explicitAPI")),
            (("cmk_postprocessed", "explicit_password", ("uuid", "explicitAPI"))),
            id="Explicit password back",
        ),
        pytest.param(
            (("store", "password_1")),
            (("cmk_postprocessed", "stored_password", ("password_1", ""))),
            id="Stored password back",
        ),
    ],
)
def test_password_back(
    raw_value: tuple[str], expected_value: tuple[str, str, tuple[str, str]]
) -> None:
    converted = migrate_password_back(raw_value)

    assert converted[0:2] == expected_value[0:2]
    assert converted[2][0].startswith(expected_value[2][0])
    assert converted[2][1] == expected_value[2][1]


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            (("cmk_postprocessed", "explicit_password", ("throwaway-id", "explicitAPI"))),
            (("password", "explicitAPI")),
            id="Explicit password forth",
        ),
        pytest.param(
            (("cmk_postprocessed", "stored_password", ("password_1", ""))),
            (("store", "password_1")),
            id="Stored password forth",
        ),
    ],
)
def test_password_forth(
    raw_value: tuple[str, str, tuple[str, str]], expected_value: tuple[str]
) -> None:
    assert migrate_password_forth(raw_value) == expected_value


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            (("cmk_postprocessed", "environment_proxy", "")),
            (("environment", "environment")),
            id="Env proxy forth",
        ),
        pytest.param(
            (("cmk_postprocessed", "no_proxy", "")),
            (("no_proxy", None)),
            id="No proxy forth",
        ),
        pytest.param(
            (("cmk_postprocessed", "explicit_proxy", "http://explicitProxy")),
            (("url", "http://explicitProxy")),
            id="Url proxy forth",
        ),
    ],
)
def test_proxy_forth(raw_value: tuple[str], expected_value: tuple[str]) -> None:
    assert migrate_proxy_forth(raw_value) == expected_value
