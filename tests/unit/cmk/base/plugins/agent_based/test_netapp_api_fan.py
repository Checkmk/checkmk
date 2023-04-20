#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import netapp_api_fan as naf
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils import netapp_api

STRING_TABLE = [
    [
        "cooling-element-list 0",
        "cooling-element-number 1",
        "rpm 3000",
        "cooling-element-is-error false",
    ],
    [
        "cooling-element-list 0",
        "cooling-element-number 2",
        "rpm 3000",
        "cooling-element-is-error true",
    ],
    [
        "cooling-element-list 0",
        "cooling-element-number 3",
        "rpm 3000",
        "cooling-element-is-error false",
    ],
    [
        "cooling-element-list 0",
        "cooling-element-number 4",
        "rpm 3020",
        "cooling-element-is-error false",
    ],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> netapp_api.SectionSingleInstance:
    return naf.parse_netapp_api_fan(STRING_TABLE)


def test_disovery_single(section: netapp_api.SectionSingleInstance) -> None:
    assert sorted(naf.netapp_api.discover_single({"mode": "single"}, section)) == [
        Service(item="0/1"),
        Service(item="0/2"),
        Service(item="0/3"),
        Service(item="0/4"),
    ]
    assert not list(naf.netapp_api.discover_summary({"mode": "single"}, section))


def test_disovery_summary(section: netapp_api.SectionSingleInstance) -> None:
    assert not list(naf.netapp_api.discover_single({"mode": "summary"}, section))
    assert list(naf.netapp_api.discover_summary({"mode": "summary"}, section)) == [
        Service(item="Summary"),
    ]


def test_check_ok(section: netapp_api.SectionSingleInstance) -> None:
    assert list(naf.netapp_api.get_single_check("fan")("0/1", section)) == [
        Result(state=State.OK, summary="Operational state OK"),
    ]


def test_check_failed(section: netapp_api.SectionSingleInstance) -> None:
    assert list(naf.netapp_api.get_single_check("fan")("0/2", section)) == [
        Result(state=State.CRIT, summary="Error in fan 2"),
    ]


def test_check_summary(section: netapp_api.SectionSingleInstance) -> None:
    assert list(naf.netapp_api.get_summary_check("fan")("Summary", section)) == [
        Result(state=State.OK, summary="OK: 3 of 4"),
        Result(state=State.CRIT, summary="Failed: 1 (0/2)"),
    ]
