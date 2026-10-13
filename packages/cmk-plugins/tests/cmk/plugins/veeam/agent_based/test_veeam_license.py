#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import HostLabel, Metric, Result, Service, State, StringTable
from cmk.plugins.veeam.agent_based.veeam_license import (
    check_veeam_license,
    CheckParameters,
    discovery_veeam_license,
    host_labels_veeam_license,
    monitoring_state,
    parse_veeam_license,
    VeeamLicense,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch

PARAMS = CheckParameters(
    license_expiry=("fixed", (30 * 86400.0, 7 * 86400.0)),
    support_expiry=("fixed", (30 * 86400.0, 7 * 86400.0)),
    consumption=("fixed", (80.0, 95.0)),
)


def _license(**overrides: object) -> list[list[str]]:
    license_dict: dict[str, object] = {
        "status": "Valid",
        "edition": "Enterprise Plus",
        "type": "Perpetual",
        "licensedTo": "ACME Corp",
        "autoUpdateEnabled": True,
    }
    license_dict.update(overrides)
    return [[json.dumps(license_dict)]]


def test_discovery_veeam_license() -> None:
    section = parse_veeam_license(_license())
    assert list(discovery_veeam_license(section)) == [Service()]


def test_parse_veeam_license() -> None:
    section = parse_veeam_license(
        _license(
            expirationDate="2027-01-21T00:00:00.000+00:00",
            supportExpirationDate="2027-06-21T00:00:00.000+00:00",
            instanceLicenseSummary={"licensedInstancesNumber": 100, "usedInstancesNumber": 50},
        )
    )
    assert section == VeeamLicense(
        status="Valid",
        edition="Enterprise Plus",
        type="Perpetual",
        expiration_date=parse_iso8601_epoch("2027-01-21T00:00:00.000+00:00"),
        support_expiration_date=parse_iso8601_epoch("2027-06-21T00:00:00.000+00:00"),
        licensed_to="ACME Corp",
        auto_update_enabled=True,
        instances_licensed=100,
        instances_used=50,
        sockets_licensed=None,
        sockets_used=None,
        capacity_licensed_tb=None,
        capacity_used_tb=None,
    )


@pytest.mark.parametrize(
    "status, expected",
    [
        pytest.param("Valid", State.OK, id="valid"),
        pytest.param("Invalid", State.CRIT, id="invalid"),
        pytest.param("Expired", State.CRIT, id="expired"),
        pytest.param("Kaputt", State.UNKNOWN, id="unparsable"),
    ],
)
def test_monitoring_state(status: str, expected: State) -> None:
    assert monitoring_state(status) == expected


def test_check_veeam_license_summary_and_details() -> None:
    section = parse_veeam_license(_license())
    results = list(check_veeam_license(PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="Enterprise Plus, Valid")
    assert Result(state=State.OK, summary="Licensed to: ACME Corp") in results
    assert Result(state=State.OK, summary="Type: Perpetual") in results
    assert Result(state=State.OK, summary="Auto update: enabled") in results


def test_check_veeam_license_omits_type_when_absent() -> None:
    section = parse_veeam_license(_license(type=None))
    results = list(check_veeam_license(PARAMS, section))
    assert not any(isinstance(r, Result) and r.summary.startswith("Type:") for r in results)


def test_check_veeam_license_invalid_is_crit() -> None:
    section = parse_veeam_license(_license(status="Invalid"))
    results = list(check_veeam_license(PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="Enterprise Plus, Invalid")


def test_check_veeam_license_no_expiry_reports_nothing() -> None:
    section = parse_veeam_license(_license())
    results = list(check_veeam_license(PARAMS, section))
    assert not any(isinstance(r, Metric) and r.name == "veeam_license_expiry" for r in results)


def test_check_veeam_license_future_expiry_reports_remaining_time() -> None:
    section = parse_veeam_license(_license(expirationDate="2999-01-21T00:00:00.000+00:00"))
    results = list(check_veeam_license(PARAMS, section))
    assert any(isinstance(r, Result) and r.summary.startswith("License expiry:") for r in results)
    assert any(isinstance(r, Metric) and r.name == "veeam_license_expiry" for r in results)


def test_check_veeam_license_past_expiry_is_crit_and_says_expired() -> None:
    section = parse_veeam_license(_license(expirationDate="2019-01-21T00:00:00.000+00:00"))
    results = list(check_veeam_license(PARAMS, section))
    assert any(
        isinstance(r, Result) and r.state is State.CRIT and "expired" in r.summary for r in results
    )
    assert any(isinstance(r, Metric) and r.name == "veeam_license_expiry" for r in results)


def test_check_veeam_license_past_expiry_can_be_silenced_with_no_levels() -> None:
    params = CheckParameters(
        license_expiry=("no_levels", None),
        support_expiry=("fixed", (30 * 86400.0, 7 * 86400.0)),
        consumption=("fixed", (80.0, 95.0)),
    )
    section = parse_veeam_license(_license(expirationDate="2019-01-21T00:00:00.000+00:00"))
    results = list(check_veeam_license(params, section))
    assert any(
        isinstance(r, Result) and r.state is State.OK and "expired" in r.summary for r in results
    )


def test_check_veeam_license_instances_consumption_metric() -> None:
    section = parse_veeam_license(
        _license(instanceLicenseSummary={"licensedInstancesNumber": 100, "usedInstancesNumber": 50})
    )
    results = list(check_veeam_license(PARAMS, section))
    assert Metric("veeam_license_instances_percent", 50.0, levels=(80.0, 95.0)) in results


def test_check_veeam_license_zero_licensed_omits_consumption() -> None:
    section = parse_veeam_license(
        _license(instanceLicenseSummary={"licensedInstancesNumber": 0, "usedInstancesNumber": 0})
    )
    results = list(check_veeam_license(PARAMS, section))
    assert not any(
        isinstance(r, Metric) and r.name == "veeam_license_instances_percent" for r in results
    )


def test_check_veeam_license_sockets_and_capacity_are_independent_of_instances() -> None:
    section = parse_veeam_license(
        _license(socketLicenseSummary={"licensedSocketsNumber": 10, "usedSocketsNumber": 9})
    )
    results = list(check_veeam_license(PARAMS, section))
    assert Metric("veeam_license_sockets_percent", 90.0, levels=(80.0, 95.0)) in results
    assert not any(
        isinstance(r, Metric) and r.name == "veeam_license_instances_percent" for r in results
    )


# Example response of GET /api/v1/license (VBR 13 REST API reference), without the
# per-workload details
STRING_TABLE: StringTable = [
    [
        (
            '{"status": "Valid", "type": "Subscription", "edition": "EnterprisePlus",'
            ' "cloudConnect": "Disabled", "licensedTo": "Veeam Software Group GmbH",'
            ' "instanceLicenseSummary": {"package": "Backup", "licensedInstancesNumber": 100,'
            ' "usedInstancesNumber": 4, "newInstancesNumber": 0, "rentalInstancesNumber": 0,'
            ' "expirationDate": "2026-12-12T00:00:00Z"}, "supportId": "02067762",'
            ' "autoUpdateEnabled": true, "freeAgentInstanceConsumptionEnabled": true,'
            ' "IsMultiSection": false, "proactiveSupportEnabled": true}'
        )
    ]
]


def test_host_labels_veeam_license_sets_the_edition() -> None:
    assert list(host_labels_veeam_license(parse_veeam_license(STRING_TABLE))) == [
        HostLabel("cmk/veeam_vbr/edition", "EnterprisePlus"),
    ]
