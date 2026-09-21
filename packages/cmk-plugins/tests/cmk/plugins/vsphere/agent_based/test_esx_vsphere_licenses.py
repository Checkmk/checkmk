#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based.esx_vsphere_licenses import (
    check_esx_vsphere_licenses,
    discover_esx_vsphere_licenses,
    parse_esx_vsphere_licenses,
)

ENTERPRISE_PLUS = "VMware vSphere 8 Enterprise Plus"
VCENTER_STANDARD = "vCenter Server 8 Standard"
STRING_TABLE = [
    [ENTERPRISE_PLUS, "16 64"],
    [ENTERPRISE_PLUS, "8 32"],
    [VCENTER_STANDARD, "1 1"],
]
ALWAYS_OK = {"levels": ("always_ok", False)}


def _check(item: str, params: Mapping[str, object]) -> list[Result | Metric]:
    results: CheckResult = check_esx_vsphere_licenses(
        item, params, parse_esx_vsphere_licenses(STRING_TABLE)
    )
    return [result for result in results if isinstance(result, Result | Metric)]


def _used_result(results: list[Result | Metric]) -> Result:
    return next(r for r in results if isinstance(r, Result) and r.summary.startswith("Used"))


def _metric(results: list[Result | Metric]) -> Metric:
    return next(r for r in results if isinstance(r, Metric))


def test_each_license_name_is_discovered_once() -> None:
    services = list(discover_esx_vsphere_licenses(parse_esx_vsphere_licenses(STRING_TABLE)))

    assert services == [Service(item=ENTERPRISE_PLUS), Service(item=VCENTER_STANDARD)]


def test_license_keys_with_the_same_name_are_summed_up() -> None:
    results = _check(ENTERPRISE_PLUS, ALWAYS_OK)

    assert Result(state=State.OK, summary="2 Key(s)") in results
    assert Result(state=State.OK, summary="Total licenses: 96") in results
    assert _metric(results).value == 24.0


def test_unknown_license_yields_nothing() -> None:
    assert _check("VMware vSAN", ALWAYS_OK) == []


def test_always_ok_does_not_alert_even_when_all_licenses_are_used() -> None:
    results = _check(VCENTER_STANDARD, ALWAYS_OK)

    assert _used_result(results).state is State.OK
    assert _metric(results).levels == (None, None)
