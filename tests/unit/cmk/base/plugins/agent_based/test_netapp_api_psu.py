#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.base.plugins.agent_based import netapp_api_psu as nap
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils import netapp_api

STRING_TABLE = [
    [
        "power-supply-list 0",
        "is-auto-power-reset-enabled false",
        "power-supply-part-no 114-00065+A2",
        "power-supply-serial-no XXT133880145",
        "power-supply-is-error false",
        "power-supply-firmware-revision 020F",
        "power-supply-type 9C",
        "power-supply-swap-count 0",
        "power-supply-element-number 1",
    ],
    [
        "power-supply-list 0",
        "is-auto-power-reset-enabled false",
        "power-supply-part-no 114-00065+A2",
        "power-supply-serial-no XXT133880140",
        "power-supply-is-error true",
        "power-supply-firmware-revision 020F",
        "power-supply-type 9C",
        "power-supply-swap-count 0",
        "power-supply-element-number 2",
    ],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> netapp_api.SectionSingleInstance:
    return nap.parse_netapp_api_psu(STRING_TABLE)


def test_disovery_single(section: netapp_api.SectionSingleInstance) -> None:
    assert sorted(nap.discovery_netapp_api_psu({"mode": "single"}, section)) == [
        Service(item="0/1"),
        Service(item="0/2"),
    ]
    assert not list(nap.discovery_netapp_api_psu_summary({"mode": "single"}, section))


def test_disovery_summary(section: netapp_api.SectionSingleInstance) -> None:
    assert not list(nap.discovery_netapp_api_psu({"mode": "summary"}, section))
    assert list(nap.discovery_netapp_api_psu_summary({"mode": "summary"}, section)) == [
        Service(item="Summary"),
    ]


def test_check_ok(section: netapp_api.SectionSingleInstance) -> None:
    assert list(nap.check_netapp_api_psu("0/1", section)) == [
        Result(state=State.OK, summary="Operational state OK"),
    ]


def test_check_failed(section: netapp_api.SectionSingleInstance) -> None:
    assert list(nap.check_netapp_api_psu("0/2", section)) == [
        Result(state=State.CRIT, summary="Error in PSU 2"),
    ]


def test_check_summary(section: netapp_api.SectionSingleInstance) -> None:
    assert list(nap.check_netapp_api_psu_summary("Summary", section)) == [
        Result(state=State.OK, summary="2 power supply units in total"),
        Result(state=State.CRIT, summary="1 power supply unit in error state (0/2)"),
    ]
