#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import datetime
from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.azure_v2.agent_based.azure_ad import (
    check_azure_ad_sync,
    discover_azure_ad_sync,
    parse_azure_ad,
)

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


def test_parse_azure_ad_sync() -> None:
    parsed = parse_azure_ad(STRING_TABLE)
    assert parsed["Standardverzeichnis"]["onPremisesLastSyncDateTime"] == "1970-02-01T00:15:01Z"
    assert parsed["Standardverzeichnis"]["onPremisesLastSyncDateTime_parsed"] == 2679301


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(STRING_TABLE, [Service(item="Standardverzeichnis")]),
        pytest.param(STRING_TABLE_SYNC_NULL, []),
        pytest.param(STRING_TABLE_SYNC_FALSE, [Service(item=("Standardverzeichnis"))]),
    ],
)
def test_discover_sync(string_table: StringTable, expected: DiscoveryResult) -> None:
    parsed_string_table = parse_azure_ad(string_table)
    assert list(discover_azure_ad_sync(parsed_string_table)) == expected


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"age": ("fixed", (3600, 7200))},
            [
                Result(
                    state=State.CRIT,
                    summary="Time since last synchronization: 2 hours 45 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
                )
            ],
            id="default params",
        ),
        pytest.param(
            {"age": None},
            [
                Result(
                    state=State.OK,
                    summary="Time since last synchronization: 2 hours 45 minutes",
                )
            ],
            id="levels disabled",
        ),
    ],
)
@time_machine.travel(datetime.datetime.fromisoformat("1970-02-01T03:00:01Z"))
def test_check_azure_sync(params: Mapping[str, Any], expected_result: CheckResult) -> None:
    parsed = parse_azure_ad(STRING_TABLE)
    assert list(check_azure_ad_sync("Standardverzeichnis", params, parsed)) == expected_result
