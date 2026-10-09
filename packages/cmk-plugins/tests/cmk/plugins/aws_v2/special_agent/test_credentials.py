#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.credentials import (
    AccessKey,
    AssumedRole,
    AwsCredentials,
    HubCredentials,
    role_session_name,
    SpokeAccounts,
)


@pytest.mark.parametrize(
    "site, expected",
    [
        pytest.param("mysite", "checkmk-mysite", id="site"),
        pytest.param(None, "checkmk", id="no site"),
        pytest.param("", "checkmk", id="empty site"),
    ],
)
def test_role_session_name_names_the_site(site: str | None, expected: str) -> None:
    assert role_session_name(site) == expected


def test_assumed_role_cannot_be_combined_with_spoke_accounts() -> None:
    hub = HubCredentials(
        AccessKey("AKIAHUB", "secret"), AssumedRole("arn:aws:iam::222222222222:role/Other")
    )

    with pytest.raises(ValueError):
        AwsCredentials(hub, "us-east-1", None, SpokeAccounts(["333333333333"], "CheckmkMonitoring"))
