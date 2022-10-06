#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

import pytest

from cmk.special_agents import agent_cisco_meraki


class FakeGetOrganisationIDsCache:
    def get_live_data(self) -> Sequence[str]:
        return ["123", "456", "789"]


class FakeOrganisations:
    def getOrganizations(self) -> Sequence[Mapping]:
        return [
            {"organizationId": "123"},
            {"organizationId": "456"},
        ]

    def getOrganizationLicensesOverview(self, organisation_id: str) -> Mapping | None:
        return None if organisation_id == "789" else {"organizationId": organisation_id}


class FakeDashboard:
    organizations = FakeOrganisations()


@pytest.mark.parametrize(
    "args, expected_output_lines",
    [
        ([], [""]),
        (
            [
                "--sections",
                "licenses-overview",
            ],
            [
                "<<<cisco_meraki_org_licenses_overview:sep(0)>>>",
                '[{"organizationId": "123"}, {"organizationId": "456"}]',
            ],
        ),
        (
            [
                "--sections",
                "licenses-overview",
                "--orgs",
                "123",
                "456",
                "789",
            ],
            [
                "<<<cisco_meraki_org_licenses_overview:sep(0)>>>",
                '[{"organizationId": "123"}, {"organizationId": "456"}]',
            ],
        ),
    ],
)
def test_agent_cisco_meraki_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: Sequence[str],
    expected_output_lines: Sequence[str],
) -> None:
    monkeypatch.setattr(
        agent_cisco_meraki,
        "_configure_meraki_dashboard",
        lambda a, b, c: FakeDashboard(),
    )
    monkeypatch.setattr(
        agent_cisco_meraki,
        "GetOrganisationIDsCache",
        lambda a: FakeGetOrganisationIDsCache(),
    )

    agent_cisco_meraki.agent_cisco_meraki_main(
        agent_cisco_meraki.parse_arguments(
            [
                "testhost",
                "my-api-key",
            ]
            + list(args)
        )
    )

    captured = capsys.readouterr()
    assert captured.out.rstrip().split("\n") == expected_output_lines
    assert captured.err == ""
