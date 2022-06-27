#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Sequence

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.oracle_crs_res import check, discover, parse, Resource, Section


@pytest.fixture(name="string_table")
def fixture_string_table():
    agent_output = """nodename|crsnode
csslocal|NAME=ora.cluster_interconnect.haip
csslocal|TYPE=ora.haip.type
csslocal|STATE=ONLINE on crsnode
csslocal|TARGET=ONLINE
NAME=ora.DG_CLUSTER.dg
TYPE=ora.diskgroup.type
STATE=ONLINE on host3
TARGET=ONLINE
host2|NAME=ora.DG_CLUSTER.dg
host2|TYPE=ora.diskgroup.type
host2|STATE=ONLINE on host2
host2|TARGET=ONLINE
oracle_host|NAME=ora.DG_CLUSTER.dg
oracle_host|TYPE=ora.diskgroup.type
oracle_host|STATE=OFF on oracle_host
oracle_host|TARGET=ONLINE"""
    return [line.split("|") for line in agent_output.split("\n")]


@pytest.fixture(name="section")
def fixture_section(string_table: StringTable) -> Section:
    return parse(string_table)


def test_parse(section: Section) -> None:
    expected_section = Section(
        crs_nodename="crsnode",
        resources={
            "ora.DG_CLUSTER.dg": {
                "host2": Resource(
                    type="ora.diskgroup.type", state="ONLINE on host2", target="ONLINE"
                ),
                "oracle_host": Resource(
                    type="ora.diskgroup.type", state="OFF on oracle_host", target="ONLINE"
                ),
                None: Resource(type="ora.diskgroup.type", state="ONLINE on host3", target="ONLINE"),
            },
            "ora.cluster_interconnect.haip": {
                "csslocal": Resource(
                    type="ora.haip.type", state="ONLINE on crsnode", target="ONLINE"
                )
            },
        },
    )
    assert section == expected_section


def test_discover(section: Section) -> None:
    services = list(discover(section))
    assert services == [
        Service(item="ora.cluster_interconnect.haip"),
        Service(item="ora.DG_CLUSTER.dg"),
    ]


@pytest.mark.parametrize(
    "item, summary",
    [
        ("ora.cssd", "Clusterware not running"),
        ("ora.crsd", "Cluster resource service daemon not running"),
    ],
)
def test_check_item_not_in_section(section: Section, item: str, summary: str) -> None:
    results = list(check(item=item, section=section))
    assert results == [Result(state=State.CRIT, summary=summary)]


def test_check_item_not_in_section_and_cluster_down(section: Section) -> None:
    with pytest.raises(IgnoreResultsError):
        list(check(item="foo", section=section))


@pytest.mark.parametrize(
    "item, results",
    [
        (
            "ora.DG_CLUSTER.dg",
            [
                Result(state=State.OK, summary="online"),
                Result(state=State.OK, summary="on host2: online"),
                Result(state=State.CRIT, summary="on oracle_host: off, target state online"),
            ],
        ),
        ("ora.cluster_interconnect.haip", [Result(state=State.OK, summary="local: online")]),
    ],
)
def test_check_item_in_section(section: Section, item: str, results: Sequence[Result]) -> None:
    assert results == list(check(item=item, section=section))
