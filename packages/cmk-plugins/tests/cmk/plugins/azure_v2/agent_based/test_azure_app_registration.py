#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.azure_app_registration import (
    check_app_registration_certificate,
    check_app_registration_secret,
    Credential,
    discover_certificates,
    discover_secrets,
    Params,
    parse_app_registration,
    Section,
)

DAY = 24 * 60 * 60.0

SECTION = Section(
    secrets={
        "srv-whatever - MyKey-bfd9d3a3": Credential(
            appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
            appName="srv-whatever",
            startDateTime="2021-09-15T09:41:12.655Z",
            endDateTime="2023-11-05T09:40:39.655Z",
            keyId="724fd654-4440-4209-9a83-39b9bfd9d3a3",
            customKeyIdentifier="MyKey",
            displayName=None,
        ),
        "srv-whatever - no-start-date-bfd9d3a4": Credential(
            appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
            appName="srv-whatever",
            startDateTime=None,
            endDateTime="2023-11-05T09:40:39.655Z",
            keyId="724fd654-4440-4209-9a83-39b9bfd9d3a4",
            customKeyIdentifier="no-start-date",
            displayName=None,
        ),
        "srv-whatever - Very very secure-bfd9d3a2": Credential(
            appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
            appName="srv-whatever",
            displayName="Very very secure",
            startDateTime="2021-09-15T09:41:12.655Z",
            endDateTime="2023-11-05T09:40:39.655Z",
            keyId="724fd654-4440-4209-9a83-39b9bfd9d3a2",
        ),
        "srv-whatever - MyVault-799a984e": Credential(
            appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
            appName="srv-whatever",
            displayName="MyVault",
            startDateTime="2022-04-05T08:25:51.097Z",
            endDateTime="2022-04-05T08:25:51.097Z",
            keyId="0cc3fc97-d36a-43e8-a4fb-c9ed799a984e",
        ),
    },
    certificates={
        "srv-whatever - the best description-4d120265": Credential(
            appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
            appName="srv-whatever",
            startDateTime="2021-11-29T11:55:54Z",
            endDateTime="2043-11-29T11:55:54Z",
            keyId="d72e9c3a-91db-4b93-ba93-cdc24d120265",
            customKeyIdentifier="B999CDD173508AC44705089C8C88FBBEA02B40CD",
            displayName="the best description",
        )
    },
)


@pytest.mark.parametrize(
    "string_table, expcted_section",
    [
        (
            [
                [
                    '{"passwordCredentials": [{"customKeyIdentifier": null, "displayName": "Very very secure", "endDateTime": "2023-11-05T09:40:39.655Z", "hint": "hi0", "keyId": "724fd654-4440-4209-9a83-39b9bfd9d3a2", "secretText": null, "startDateTime": "2021-09-15T09:41:12.655Z"}, {"customKeyIdentifier": null, "displayName": "MyVault", "endDateTime": "2022-04-05T08:25:51.097Z", "hint": "gU1", "keyId": "0cc3fc97-d36a-43e8-a4fb-c9ed799a984e", "secretText": null, "startDateTime": "2022-04-05T08:25:51.097Z"}, {"customKeyIdentifier": "MyKey", "displayName": null, "endDateTime": "2023-11-05T09:40:39.655Z", "hint": "hi0", "keyId": "724fd654-4440-4209-9a83-39b9bfd9d3a3", "secretText": null, "startDateTime": "2021-09-15T09:41:12.655Z"},{"customKeyIdentifier": "no-start-date", "displayName": null, "endDateTime": "2023-11-05T09:40:39.655Z", "hint": "hi0", "keyId": "724fd654-4440-4209-9a83-39b9bfd9d3a4", "secretText": null}], '
                    '"displayName": "srv-whatever", "id": "cd02b35f-c07b-40e2-82fb-e1f8b1907c4f", "appId": "9c677ced-6cb2-44b3-af54-65f768065fdf",'
                    '"keyCredentials": [{"customKeyIdentifier": "B999CDD173508AC44705089C8C88FBBEA02B40CD", "displayName": "the best description", "endDateTime": "2043-11-29T11:55:54Z", "keyId": "d72e9c3a-91db-4b93-ba93-cdc24d120265", "startDateTime": "2021-11-29T11:55:54Z"}]}'
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
                Service(item="srv-whatever - MyKey-bfd9d3a3"),
                Service(item="srv-whatever - no-start-date-bfd9d3a4"),
                Service(item="srv-whatever - Very very secure-bfd9d3a2"),
                Service(item="srv-whatever - MyVault-799a984e"),
            ],
        )
    ],
)
def test_discover_secrets(section: Section, expected_discovery: DiscoveryResult) -> None:
    assert list(discover_secrets(section)) == expected_discovery


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        (
            SECTION,
            [
                Service(item="srv-whatever - the best description-4d120265"),
            ],
        )
    ],
)
def test_discover_certificates(section: Section, expected_discovery: DiscoveryResult) -> None:
    assert list(discover_certificates(section)) == expected_discovery


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        pytest.param(
            "srv-whatever - MyVault-799a984e",
            {},
            Section(secrets={}, certificates={}),
            [],
            id="item_missing",
        ),
        pytest.param(
            "srv-whatever - Very very secure-bfd9d3a2",
            {"secrets": {"remaining_validity": ("fixed", (500 * DAY, 100 * DAY))}},
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
            "srv-whatever - MyVault-799a984e",
            {"secrets": {"remaining_validity": ("fixed", (30 * DAY, 7 * DAY))}},
            SECTION,
            [Result(state=State.CRIT, summary="Secret expired: 230 days 15 hours ago")],
            id="secret_expired",
        ),
        pytest.param(
            "srv-whatever - MyVault-799a984e",
            {"secrets": {"ignore_if_older_than": 1 * 24 * 60 * 60}},
            SECTION,
            [Result(state=State.OK, summary="Secret ignored: expired more than 1 day 0 hours ago")],
            id="secret_expired_ignored",
        ),
        pytest.param(
            "srv-whatever - Very very secure-bfd9d3a2",
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Remaining time: 348 days 9 hours"),
            ],
            id="secret_no_levels_configured",
        ),
        pytest.param(
            "srv-whatever - no-start-date-bfd9d3a4",
            {
                "secrets": {
                    "max_validity": ("fixed", (400 * DAY, 600 * DAY)),
                }
            },
            SECTION,
            [
                Result(state=State.OK, summary="Remaining time: 348 days 9 hours"),
            ],
            id="secret_no_start_date",
        ),
        pytest.param(
            "srv-whatever - long-lived-00000001",
            {
                "secrets": {
                    "remaining_validity": ("fixed", (30 * DAY, 7 * DAY)),
                    "max_validity": ("fixed", (400 * DAY, 600 * DAY)),
                }
            },
            Section(
                secrets={
                    "srv-whatever - long-lived-00000001": Credential(
                        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
                        appName="srv-whatever",
                        startDateTime="2020-01-01T00:00:00Z",
                        endDateTime="2024-01-01T00:00:00Z",
                        keyId="00000000-0000-0000-0000-000000000001",
                    )
                },
                certificates={},
            ),
            [
                Result(state=State.OK, summary="Remaining time: 1 year 40 days"),
                Result(
                    state=State.CRIT,
                    summary="Max validity: 4 years 1 day (warn/crit at 1 year 35 days/1 year 235 days)",
                ),
            ],
            id="secret_max_validity_exceeded",
        ),
        pytest.param(
            "srv-whatever - MyVault-799a984e",
            {
                "secrets": {
                    "remaining_validity": ("fixed", (30 * DAY, 7 * DAY)),
                    "ignore_if_older_than": 3000 * DAY,
                }
            },
            SECTION,
            [Result(state=State.CRIT, summary="Secret expired: 230 days 15 hours ago")],
            id="secret_not_ignored_threshold_not_reached",
        ),
        pytest.param(
            "srv-whatever - Very very secure-bfd9d3a2",
            {
                "secrets": {
                    "remaining_validity": ("fixed", (30 * DAY, 7 * DAY)),
                    "ignore_if_older_than": 100 * DAY,
                }
            },
            SECTION,
            [Result(state=State.OK, summary="Remaining time: 348 days 9 hours")],
            id="secret_not_expired_ignore_not_applied",
        ),
    ],
)
def test_check_app_registration_secret(
    item: str,
    params: Params,
    section: Section,
    expected_result: CheckResult,
) -> None:
    with time_machine.travel(datetime.datetime(2022, 11, 22, tzinfo=ZoneInfo("UTC"))):
        assert list(check_app_registration_secret(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        pytest.param(
            "srv-whatever - long-cert-00000002",
            {
                "certificates": {
                    "remaining_validity": ("fixed", (30 * DAY, 7 * DAY)),
                    "max_validity": ("fixed", (400 * DAY, 600 * DAY)),
                }
            },
            Section(
                secrets={},
                certificates={
                    "srv-whatever - long-cert-00000002": Credential(
                        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
                        appName="srv-whatever",
                        startDateTime="2020-01-01T00:00:00Z",
                        endDateTime="2024-01-01T00:00:00Z",
                        keyId="00000000-0000-0000-0000-000000000002",
                    )
                },
            ),
            [
                Result(state=State.OK, summary="Remaining time: 1 year 40 days"),
                Result(
                    state=State.CRIT,
                    summary="Max validity: 4 years 1 day (warn/crit at 1 year 35 days/1 year 235 days)",
                ),
            ],
            id="certificate_max_validity_exceeded",
        ),
        pytest.param(
            "srv-whatever - the best description-4d120265",
            {
                "certificates": {
                    "remaining_validity": ("fixed", (30 * DAY, 7 * DAY)),
                    "ignore_if_older_than": 300 * DAY,
                }
            },
            SECTION,
            [Result(state=State.OK, summary="Remaining time: 21 years 12 days")],
            id="certificate_not_ignored_not_expired",
        ),
        pytest.param(
            "srv-whatever - expired-cert-00000003",
            {"certificates": {"ignore_if_older_than": 1 * DAY}},
            Section(
                secrets={},
                certificates={
                    "srv-whatever - expired-cert-00000003": Credential(
                        appId="9c677ced-6cb2-44b3-af54-65f768065fdf",
                        appName="srv-whatever",
                        startDateTime="2022-01-01T00:00:00Z",
                        endDateTime="2022-04-05T08:25:51.097Z",
                        keyId="00000000-0000-0000-0000-000000000003",
                        displayName="expired-cert",
                    )
                },
            ),
            [
                Result(
                    state=State.OK,
                    summary="Certificate ignored: expired more than 1 day 0 hours ago",
                )
            ],
            id="certificate_expired_ignored",
        ),
    ],
)
def test_check_app_registration_certificate(
    item: str, params: Params, section: Section, expected_result: CheckResult
) -> None:
    with time_machine.travel(datetime.datetime(2022, 11, 22, tzinfo=ZoneInfo("UTC"))):
        assert list(check_app_registration_certificate(item, params, section)) == expected_result
