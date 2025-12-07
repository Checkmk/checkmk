#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based.sap_hana_ess import (
    check_plugin_sap_hana_ess,
    parse_sap_hana_ess,
)


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no", "started": 0}},
        ),
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no"}},
        ),
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "a"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no"}},
        ),
    ],
)
def test_parse_sap_hana_ess(info: StringTable, expected_result: Mapping[str, object]) -> None:
    result = parse_sap_hana_ess(info)
    assert result == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            [Service(item="HXE 90 HXE")],
        ),
    ],
)
def test_inventory_sap_hana_ess(info: StringTable, expected_result: DiscoveryResult) -> None:
    section = parse_sap_hana_ess(info)
    assert list(check_plugin_sap_hana_ess.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            [
                Result(state=State.CRIT, summary="Active status: no"),
                Result(state=State.CRIT, summary="Started threads: 0"),
                Metric("threads", 0),
            ],
        ),
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "1"],
                ["active", "yes"],
            ],
            [
                Result(state=State.OK, summary="Active status: yes"),
                Result(state=State.OK, summary="Started threads: 1"),
                Metric("threads", 1),
            ],
        ),
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "1"],
                ["active", "unknown"],
            ],
            [
                Result(state=State.UNKNOWN, summary="Active status: unknown"),
                Result(state=State.OK, summary="Started threads: 1"),
                Metric("threads", 1),
            ],
        ),
    ],
)
def test_check_sap_hana_ess(
    item: str,
    info: StringTable,
    expected_result: CheckResult,
) -> None:
    section = parse_sap_hana_ess(info)
    assert list(check_plugin_sap_hana_ess.check_function(item, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_ess_stale(item: str, info: StringTable) -> None:
    section = parse_sap_hana_ess(info)
    with pytest.raises(IgnoreResultsError):
        list(check_plugin_sap_hana_ess.check_function(item, section))
