#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.exceptions import MKUserError
from cmk.gui.oauth.wato._settings import ConfigVariableOAuthSessions
from cmk.gui.valuespec import ValueSpec
from cmk.gui.watolib.config_domain_name import GlobalSettingsContext

_DAY = 86400


def _valuespec() -> ValueSpec[object]:
    return ConfigVariableOAuthSessions.valuespec(
        GlobalSettingsContext(
            target_site_id=SiteId("test-site"),
            edition_of_local_site=Edition.PRO,
            site_neutral_log_dir=Path(""),
            site_neutral_var_dir=Path(""),
            configured_sites=SiteConfigurations({}),
            configured_graph_timeranges=[],
        )
    )


@pytest.mark.parametrize(
    "lifetimes",
    [
        pytest.param(
            {
                "grant_lifetime": 30 * _DAY,
                "refresh_token_lifetime": 31 * _DAY,
                "access_token_lifetime": _DAY,
            },
            id="refresh token exceeds session",
        ),
        pytest.param(
            {
                "grant_lifetime": 30 * _DAY,
                "refresh_token_lifetime": _DAY,
                "access_token_lifetime": 2 * _DAY,
            },
            id="access token exceeds refresh token",
        ),
    ],
)
def test_rejects_a_token_lifetime_longer_than_what_contains_it(lifetimes: dict[str, int]) -> None:
    with pytest.raises(MKUserError):
        _valuespec().validate_value(lifetimes, "oauth_sessions")


def test_accepts_equal_lifetimes() -> None:
    _valuespec().validate_value(
        {
            "grant_lifetime": _DAY,
            "refresh_token_lifetime": _DAY,
            "access_token_lifetime": _DAY,
        },
        "oauth_sessions",
    )
