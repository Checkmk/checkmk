#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.azure.agent_based.azure_app_registration import (
    check_app_registration,
    ClientSecret,
    discover_app_registration,
    parse_app_registration,
    Section,
)

SECTION = {
    "srv-whatever - MyKey": ClientSecret(
        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
        appName="srv-whatever",
        endDateTime="2023-11-05T09:40:39.655Z",
        keyId="724fd654-4440-4209-9a83-39b9bfd9d3a3",
        customKeyIdentifier="MyKey",
        displayName=None,
    ),
    "srv-whatever - Very very secure": ClientSecret(
        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
        appName="srv-whatever",
        displayName="Very very secure",
        endDateTime="2023-11-05T09:40:39.655Z",
        keyId="724fd654-4440-4209-9a83-39b9bfd9d3a2",
    ),
    "srv-whatever - MyVault": ClientSecret(
        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
        appName="srv-whatever",
        displayName="MyVault",
        endDateTime="2022-04-05T08:25:51.097Z",
        keyId="0cc3fc97-d36a-43e8-a4fb-c9ed799a984e",
    ),
}


@pytest.mark.parametrize(
    "string_table, expcted_section",
    [
        (
            [
                [
                    '{"passwordCredentials": [{"customKeyIdentifier": null, "displayName": "Very very secure", "endDateTime": "2023-11-05T09:40:39.655Z", "hint": "hi0", "keyId": "724fd654-4440-4209-9a83-39b9bfd9d3a2", "secretText": null, "startDateTime": "2021-09-15T09:41:12.655Z"}, {"customKeyIdentifier": null, "displayName": "MyVault", "endDateTime": "2022-04-05T08:25:51.097Z", "hint": "gU1", "keyId": "0cc3fc97-d36a-43e8-a4fb-c9ed799a984e", "secretText": null, "startDateTime": "2022-04-05T08:25:51.097Z"}, {"customKeyIdentifier": "MyKey", "displayName": null, "endDateTime": "2023-11-05T09:40:39.655Z", "hint": "hi0", "keyId": "724fd654-4440-4209-9a83-39b9bfd9d3a3", "secretText": null, "startDateTime": "2021-09-15T09:41:12.655Z"}], "displayName": "srv-whatever", "id": "cd02b35f-c07b-40e2-82fb-e1f8b1907c4f", "appId": "9c677ced-6cb2-44b3-af54-65f768065fdf"}'
                ],
            ],
            SECTION,
        )
    ],
)
def test_parse_app_registration(string_table: StringTable, expcted_section: Section) -> None:
    assert parse_app_registration(string_table) == expcted_section


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        (
            SECTION,
            [
                Service(item="srv-whatever - MyKey"),
                Service(item="srv-whatever - Very very secure"),
                Service(item="srv-whatever - MyVault"),
            ],
        )
    ],
)
def test_discover_app_registration(section: Section, expected_discovery: DiscoveryResult) -> None:
    assert list(discover_app_registration(section)) == expected_discovery


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        pytest.param("srv-whatever - MyVault", {}, {}, [], id="item_missing"),
        pytest.param(
            "srv-whatever - Very very secure",
            {"expiration_time": (500 * 24 * 60 * 60, 100 * 24 * 60 * 60)},
            SECTION,
            [
                Result(
                    state=State.WARN,
                    summary="Remaining time: 348 days 9 hours (warn/crit below 1 year 135 days/100 days 0 hours)",
                )
            ],
            id="secret_still_valid",
        ),
        pytest.param(
            "srv-whatever - MyVault",
            {"expiration_time": (30 * 24 * 60 * 60, 7 * 24 * 60 * 60)},
            SECTION,
            [Result(state=State.CRIT, summary="Secret expired: 230 days 15 hours ago")],
            id="secret_expired",
        ),
    ],
)
def test_check_app_registration(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: Section,
    expected_result: CheckResult,
) -> None:
    with time_machine.travel(datetime.datetime(2022, 11, 22, tzinfo=ZoneInfo("UTC"))):
        assert list(check_app_registration(item, params, section)) == expected_result
