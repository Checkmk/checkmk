#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.sap_hana_license as sap_hana_license
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

SECTION = {
    "Y04 10": {
        "enforced": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "locked": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "expiration_date": "2020-08-02 23:59:59.999999000",
        "permanent": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "limit": 2147483647,
        "valid": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "size": 33,
    },
    "H62 10": {
        "enforced": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "locked": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "expiration_date": "?",
        "permanent": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "limit": 12300,
        "valid": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "size": 19,
    },
    "X04 55": {
        "enforced": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "locked": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "expiration_date": "2020-08-02 23:59:59.999999000",
        "permanent": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "limit": 10,
        "valid": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "size": 5,
    },
    "X00 00": {
        "enforced": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "locked": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "expiration_date": "2020-08-02 23:59:59.999999000",
        "permanent": sap_hana_license.SAP_HANA_MAYBE(bool=False, value="FALSE"),
        "limit": 0,
        "valid": sap_hana_license.SAP_HANA_MAYBE(bool=True, value="TRUE"),
        "size": 5,
    },
}


@pytest.mark.parametrize(
    "string_table_row, expected_parsed_data",
    [
        (
            [
                ["[[H62 10]]"],
                ["FALSE", "TRUE", "FALSE", "19", "12300", "TRUE", "?"],
            ],
            {"H62 10": SECTION["H62 10"]},
        ),
        (
            [
                ["[[Y04 10]]"],
                [
                    "FALSE",
                    "FALSE",
                    "FALSE",
                    "33",
                    "2147483647",
                    "TRUE",
                    "2020-08-02 23:59:59.999999000",
                ],
            ],
            {"Y04 10": SECTION["Y04 10"]},
        ),
        (
            [
                ["[[X04 55]]"],
                ["TRUE", "FALSE", "FALSE", "5", "10", "TRUE", "2020-08-02 23:59:59.999999000"],
            ],
            {"X04 55": SECTION["X04 55"]},
        ),
    ],
)
def test_sap_hana_license_parse(string_table_row, expected_parsed_data) -> None:
    assert sap_hana_license.parse_sap_hana_license(string_table_row) == expected_parsed_data


def test_sap_hana_license_discovery() -> None:
    assert list(sap_hana_license.discovery_sap_hana_license(SECTION)) == [
        Service(item="Y04 10", parameters={}, labels=[]),
        Service(item="H62 10", parameters={}, labels=[]),
        Service(item="X04 55", parameters={}, labels=[]),
        Service(item="X00 00", parameters={}, labels=[]),
    ]


@pytest.mark.parametrize(
    "cur_item, result",
    [
        (
            "Y04 10",
            [
                Result(state=state.OK, summary="Status: unlimited"),
                Result(state=state.WARN, summary="License: not FALSE"),
                Result(
                    state=state.WARN,
                    summary="Expiration date: 2020-08-02 23:59:59.999999000",
                    details="Expiration date: 2020-08-02 23:59:59.999999000",
                ),
            ],
        ),
        (
            "H62 10",
            [
                Result(state=state.OK, summary="Status: unlimited"),
                Result(state=state.OK, summary="License: TRUE"),
            ],
        ),
        (
            "X04 55",
            [
                Result(state=state.OK, summary="Size: 5 B"),
                Metric("license_size", 5.0),
                Result(state=state.OK, summary="Usage: 50.00%"),
                Metric("license_usage_perc", 50.0),
                Result(state=state.WARN, summary="License: not FALSE"),
                Result(
                    state=state.WARN,
                    summary="Expiration date: 2020-08-02 23:59:59.999999000",
                    details="Expiration date: 2020-08-02 23:59:59.999999000",
                ),
            ],
        ),
        (
            "X00 00",
            [
                Result(state=state.OK, summary="Size: 5 B"),
                Metric("license_size", 5.0),
                Result(
                    state=state.WARN,
                    summary="Usage: cannot calculate",
                    details="Usage: cannot calculate",
                ),
                Result(state=state.WARN, summary="License: not FALSE"),
                Result(
                    state=state.WARN,
                    summary="Expiration date: 2020-08-02 23:59:59.999999000",
                    details="Expiration date: 2020-08-02 23:59:59.999999000",
                ),
            ],
        ),
    ],
)
def test_sap_hana_license_check(cur_item, result) -> None:
    yielded_results = list(sap_hana_license.check_sap_hana_license(cur_item, {}, SECTION))
    assert yielded_results == result


@pytest.mark.parametrize(
    "item, section",
    [
        ("Y04 10", {"Y04 10": {}}),
    ],
)
def test_sap_hana_license_check_stale(item, section) -> None:
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_license.check_sap_hana_license(item, {}, section))
