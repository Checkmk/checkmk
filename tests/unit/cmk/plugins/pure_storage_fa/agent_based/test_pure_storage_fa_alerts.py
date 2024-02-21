#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.pure_storage_fa.agent_based.pure_storage_fa_alerts import (
    check_internal_alerts,
    discover_internal_alerts,
    InternalAlerts,
    parse_alerts,
)

ALERTS = InternalAlerts(
    critical_alerts=["boot drive overutilization"],
    warning_alerts=["high load on boot drive"],
    info_alerts=["boot drive started"],
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [
                [
                    '{"continuation_token": null, "items": [{"id": "1", "name": "string", "actual": "95%", "category": "array", "closed": 1578440492342, "code": 7, "component_name": "vm-tom", "component_type": "storage", "created": 1576275532434, "description": "boot drive overutilization", "flagged": true,"issue": "boot drive overutilization","knowledge_base_url": "https://support.purestorage.com/?cid=Alert_0007", "expected": "90%","notified": 1578440491109, "severity": "critical", "state": "open","summary": "boot drive overutilization","updated": 1578440491109}, {"id": "2", "name": "string", "actual": "95%", "category": "array", "closed": 1578440492342, "code": 7, "component_name": "vm-tom", "component_type": "storage", "created": 1576275532434, "description": "high load on boot drive", "flagged": true,"issue": "high load on boot drive","knowledge_base_url": "https://support.purestorage.com/?cid=Alert_0007", "expected": "90%","notified": 1578440491109, "severity": "warning", "state": "open","summary": "high load on boot drive","updated": 1578440491109}, {"id": "3", "name": "string", "actual": "95%", "category": "array", "closed": 1578440492342, "code": 7, "component_name": "vm-tom", "component_type": "storage", "created": 1576275532434, "description": "boot drive started", "flagged": true,"issue": "boot drive started","knowledge_base_url": "https://support.purestorage.com/?cid=Alert_0007", "expected": "90%","notified": 1578440491109, "severity": "info", "state": "open","summary": "boot drive started","updated": 1578440491109}], "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            ALERTS,
            id="alerts present",
        ),
        pytest.param(
            [
                [
                    '{"continuation_token": null, "more_items_remaining": false, "total_item_count": null}'
                ]
            ],
            InternalAlerts(critical_alerts=[], warning_alerts=[], info_alerts=[]),
            id="no alerts",
        ),
    ],
)
def test_parse_alerts(string_table: StringTable, expected_section: InternalAlerts) -> None:
    assert parse_alerts(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            ALERTS,
            [Service()],
        )
    ],
)
def test_discover_internal_alerts(
    section: InternalAlerts, expected_services: DiscoveryResult
) -> None:
    assert list(discover_internal_alerts(section)) == expected_services


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            ALERTS,
            [
                Result(state=State.CRIT, summary="Critical: 1"),
                Result(state=State.OK, notice="Critical alerts: boot drive overutilization"),
                Result(state=State.WARN, summary="Warning: 1"),
                Result(state=State.OK, notice="Warning alerts: high load on boot drive"),
                Result(state=State.OK, summary="Info: 1"),
                Result(state=State.OK, notice="Info alerts: boot drive started"),
            ],
            id="alerts present",
        ),
        pytest.param(
            InternalAlerts(critical_alerts=[], warning_alerts=[], info_alerts=[]),
            [
                Result(state=State.OK, summary="Critical: 0"),
                Result(state=State.OK, summary="Warning: 0"),
                Result(state=State.OK, summary="Info: 0"),
            ],
            id="no alerts",
        ),
    ],
)
def test_check_internal_alerts(
    section: InternalAlerts,
    expected_result: CheckResult,
) -> None:
    assert list(check_internal_alerts(section)) == expected_result
