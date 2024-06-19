#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.solaris_services import (
    check_solaris_services,
    check_solaris_services_summary,
    DISCOVER_NOTHING,
    discover_solaris_services,
    discover_solaris_services_summary,
    parse_solaris_services,
    Section,
)

STRING_TABLE = [
    ["STATE", "STIME", "FMRI"],
    ["online", "Jan_1", "svc1:/cat1/name1:inst1"],
    ["online", "Jan_1", "0:00:00", "svc2:/cat2/name2:inst2"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_solaris_services(STRING_TABLE)


def test_discovery_default_nothing(section: Section) -> None:
    assert not list(discover_solaris_services([DISCOVER_NOTHING], section))


def test_discovery_match_description(section: Section) -> None:
    assert list(
        discover_solaris_services(
            [
                {
                    "description": ["~Jan_?"],
                }
            ],
            section,
        )
    ) == [
        Service(item="svc1:/cat1/name1:inst1"),
        Service(item="svc2:/cat2/name2:inst2"),
    ]


def test_discovery_summary(section: Section) -> None:
    assert list(discover_solaris_services_summary(section)) == [Service()]


def check_item_not_found(section: Section) -> None:
    assert list(check_solaris_services("NotPresent", {}, section)) == [
        Result(state=State.UNKNOWN, summary=""),
    ]


def check_regular(section: Section) -> None:
    assert list(check_solaris_services("Jan_1", {}, section)) == [
        Result(state=State.UNKNOWN, summary="Service not found"),
    ]
    assert list(check_solaris_services("Jan_1", {"else": 2}, section)) == [
        Result(state=State.CRIT, summary="Service not found"),
    ]


def check_summary(section: Section) -> None:
    assert list(check_solaris_services_summary({}, section)) == [
        Result(state=State.OK, summary="1 service"),
    ]
