#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import datetime
from collections.abc import Iterable
from typing import Any

import pytest
import time_machine

from cmk.agent_based.legacy.v0_unstable import _DiscoveredParameters
from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks import azure_ad

STRING_TABLE = [
    ["users_count", "2"],
    [
        "ad_connect",
        '[{"deletedDateTime": null, "privacyProfile": null, "street": null, "countryLetterCode": "DE", "id": "93176ea2-ff16-46e0-b84e-862fba579335", "city": null, "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "fca3e605-0754-4279-8504-3f1229f29614", "service": "WindowsAzure", "assignedDateTime": "2019-05-03T14:48:51Z"}], "preferredLanguage": "de", "state": null, "securityComplianceNotificationPhones": [], "businessPhones": [], "postalCode": null, "onPremisesLastSyncDateTime": "1970-02-01T00:15:01Z", "technicalNotificationMails": ["foo@bar.baz"], "verifiedDomains": [{"name": "foobar.onmicrosoft.com", "type": "Managed", "isDefault": true, "capabilities": "Email, OfficeCommunicationsOnline", "isInitial": true}], "onPremisesSyncEnabled": true, "displayName": "Standardverzeichnis", "marketingNotificationEmails": [], "provisionedPlans": [], "createdDateTime": "2018-09-14T12:44:23Z", "country": null, "securityComplianceNotificationMails": []}]',
    ],
]

STRING_TABLE_SYNC_FALSE = [
    ["users_count", "2"],
    [
        "ad_connect",
        '[{"deletedDateTime": null, "privacyProfile": null, "street": null, "countryLetterCode": "DE", "id": "93176ea2-ff16-46e0-b84e-862fba579335", "city": null, "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "fca3e605-0754-4279-8504-3f1229f29614", "service": "WindowsAzure", "assignedDateTime": "2019-05-03T14:48:51Z"}], "preferredLanguage": "de", "state": null, "securityComplianceNotificationPhones": [], "businessPhones": [], "postalCode": null, "onPremisesLastSyncDateTime": "1970-02-01T00:15:01Z", "technicalNotificationMails": ["foo@bar.baz"], "verifiedDomains": [{"name": "foobar.onmicrosoft.com", "type": "Managed", "isDefault": true, "capabilities": "Email, OfficeCommunicationsOnline", "isInitial": true}], "onPremisesSyncEnabled": false, "displayName": "Standardverzeichnis", "marketingNotificationEmails": [], "provisionedPlans": [], "createdDateTime": "2018-09-14T12:44:23Z", "country": null, "securityComplianceNotificationMails": []}]',
    ],
]

STRING_TABLE_SYNC_NULL = [
    ["users_count", "2"],
    [
        "ad_connect",
        '[{"deletedDateTime": null, "privacyProfile": null, "street": null, "countryLetterCode": "DE", "id": "93176ea2-ff16-46e0-b84e-862fba579335", "city": null, "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "fca3e605-0754-4279-8504-3f1229f29614", "service": "WindowsAzure", "assignedDateTime": "2019-05-03T14:48:51Z"}], "preferredLanguage": "de", "state": null, "securityComplianceNotificationPhones": [], "businessPhones": [], "postalCode": null, "onPremisesLastSyncDateTime": null, "technicalNotificationMails": ["foo@bar.baz"], "verifiedDomains": [{"name": "foobar.onmicrosoft.com", "type": "Managed", "isDefault": true, "capabilities": "Email, OfficeCommunicationsOnline", "isInitial": true}], "onPremisesSyncEnabled": null, "displayName": "Standardverzeichnis", "marketingNotificationEmails": [], "provisionedPlans": [], "createdDateTime": "2018-09-14T12:44:23Z", "country": null, "securityComplianceNotificationMails": []}]',
    ],
]


def test_parse_azure_ad_sync():
    parsed = azure_ad.parse_azure_ad(STRING_TABLE)
    assert parsed["Standardverzeichnis"]["onPremisesLastSyncDateTime"] == "1970-02-01T00:15:01Z"
    assert parsed["Standardverzeichnis"]["onPremisesLastSyncDateTime_parsed"] == 2679301


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(STRING_TABLE, [("Standardverzeichnis", {})]),
        pytest.param(STRING_TABLE_SYNC_NULL, []),
        # Is it intentional that this isn't []?
        pytest.param(STRING_TABLE_SYNC_FALSE, [("Standardverzeichnis", {})]),
    ],
)
def test_discover_sync(
    string_table: StringTable, expected: Iterable[tuple[str | None, _DiscoveredParameters]]
) -> None:
    parsed_string_table = azure_ad.parse_azure_ad(string_table)
    assert azure_ad.discover_sync(parsed_string_table) == expected


@pytest.mark.parametrize(
    "params, expected_status, expected_message",
    [
        pytest.param(
            {"age": (3600, 7200)},
            2,
            "Time since last synchronization: 2 hours 45 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            id="default params",
        ),
        pytest.param(
            {"age": (None, None)},
            0,
            "Time since last synchronization: 2 hours 45 minutes",
            id="levels disabled",
        ),
    ],
)
@time_machine.travel(datetime.datetime.fromisoformat("1970-02-01 03:00:01"))
def test_check_azure_sync(
    params: dict[str, Any], expected_status: int, expected_message: str
) -> None:
    parsed = azure_ad.parse_azure_ad(STRING_TABLE)
    assert list(azure_ad.check_azure_sync("Standardverzeichnis", params, parsed)) == [
        (expected_status, expected_message, []),
    ]
