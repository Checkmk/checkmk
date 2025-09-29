#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks import azure_ad

STRING_TABLE = [
    ["users_count", "2"],
    [
        "ad_connect",
        '[{"deletedDateTime": null, "privacyProfile": null, "street": null, "countryLetterCode": "DE", "id": "93176ea2-ff16-46e0-b84e-862fba579335", "city": null, "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "fca3e605-0754-4279-8504-3f1229f29614", "service": "WindowsAzure", "assignedDateTime": "2019-05-03T14:48:51Z"}], "preferredLanguage": "de", "state": null, "securityComplianceNotificationPhones": [], "businessPhones": [], "postalCode": null, "onPremisesLastSyncDateTime": "1970-02-01T02:15:01Z", "technicalNotificationMails": ["foo@bar.baz"], "verifiedDomains": [{"name": "foobar.onmicrosoft.com", "type": "Managed", "isDefault": true, "capabilities": "Email, OfficeCommunicationsOnline", "isInitial": true}], "onPremisesSyncEnabled": true, "displayName": "Standardverzeichnis", "marketingNotificationEmails": [], "provisionedPlans": [], "createdDateTime": "2018-09-14T12:44:23Z", "country": null, "securityComplianceNotificationMails": []}]',
    ],
]


def test_discover_ad_users() -> None:
    parsed = azure_ad.parse_azure_ad(STRING_TABLE)
    assert list(azure_ad.discover_ad_users(parsed)) == [(None, {})]


def test_check_azure_users() -> None:
    parsed = azure_ad.parse_azure_ad(STRING_TABLE)
    assert list(azure_ad.check_azure_users(None, {}, parsed)) == [
        (0, "User accounts: 2", [("count", 2, None, None)]),
    ]
