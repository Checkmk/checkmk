#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State, StringTable
from cmk.plugins.oracle.agent_based.oracle_crs_res import (
    check_oracle_crs_res,
    discover_oracle_crs_res,
    parse_oracle_crs_res,
    Resource,
    Section,
)

_STRING_TABLE_BOTH_OFFLINE = [
    ["nodename", "ezszds8q"],
    ["csslocal", "NAME=ora.asm"],
    ["csslocal", "TYPE=ora.asm.type"],
    ["ezszds8q", "TYPE=ora.diskgroup.type"],
    ["ezszds8q", "STATE=ONLINE on ezszds8q"],
    ["ezszds8q", "TARGET=ONLINE"],
    ["ezszds8q", "NAME=ora.ASST_MLOG.dg"],
    ["ezszds8q", "TYPE=ora.diskgroup.type"],
    ["ezszds8q", "STATE=OFFLINE on ezszds8q"],
    ["ezszds8q", "TARGET=ONLINE"],
    ["ezszds9q", "NAME=ora.ASST_MLOG.dg"],
    ["ezszds9q", "TYPE=ora.diskgroup.type"],
    ["ezszds9q", "STATE=OFFLINE on ezszds9q"],
    ["ezszds9q", "TARGET=ONLINE"],
]


_DEFAULT_PARAMETERS_ORACLE_CRS_RES = {"number_of_nodes_not_in_target_state": (1, 2)}


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
    return parse_oracle_crs_res(string_table)


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


def test_parse_ignores_additional_enable_attribute() -> None:
    string_table = [
        ["nodename", "lllllllll"],
        ["csslocal", "NAME=ooo.ooooooooooooo.oo"],
        ["csslocal", "TYPE=rrr.rrrrrrrrr.rrrr"],
        ["csslocal", "ENABLED=1"],
        ["csslocal", "STATE=ONLINE"],
        ["csslocal", "TARGET=ONLINE"],
    ]
    assert parse_oracle_crs_res(string_table) == Section(
        crs_nodename="lllllllll",
        resources={
            "ooo.ooooooooooooo.oo": {
                "csslocal": Resource(type="rrr.rrrrrrrrr.rrrr", state="ONLINE", target="ONLINE")
            }
        },
    )


def test_discover(section: Section) -> None:
    services = list(discover_oracle_crs_res(section))
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
    results = list(
        check_oracle_crs_res(
            item=item,
            params=_DEFAULT_PARAMETERS_ORACLE_CRS_RES,
            section=section,
        )
    )
    assert results == [Result(state=State.CRIT, summary=summary)]


def test_check_item_not_in_section_and_cluster_down(section: Section) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            check_oracle_crs_res(
                item="foo",
                params=_DEFAULT_PARAMETERS_ORACLE_CRS_RES,
                section=section,
            )
        )


@pytest.mark.parametrize(
    "item, results",
    [
        pytest.param(
            "ora.DG_CLUSTER.dg",
            [
                Result(
                    state=State.WARN,
                    summary="Number of nodes not in target state: 1 (warn/crit at 1/2)",
                ),
                Metric("oracle_number_of_nodes_not_in_target_state", 1.0, levels=(1.0, 2.0)),
                Result(
                    state=State.OK,
                    summary="online; on host2: online; on oracle_host: off, target state online",
                ),
            ],
        ),
        pytest.param(
            "ora.cluster_interconnect.haip",
            [
                Result(state=State.OK, summary="Number of nodes not in target state: 0"),
                Metric("oracle_number_of_nodes_not_in_target_state", 0.0, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="local: online"),
            ],
        ),
    ],
)
def test_check_item_in_section(section: Section, item: str, results: Sequence[Result]) -> None:
    assert results == list(
        check_oracle_crs_res(
            item=item,
            params=_DEFAULT_PARAMETERS_ORACLE_CRS_RES,
            section=section,
        )
    )


@pytest.mark.parametrize(
    "item, string_table, expected_check_result",
    [
        pytest.param(
            "ora.ASST_MLOG.dg",
            _STRING_TABLE_BOTH_OFFLINE,
            [
                Result(
                    state=State.CRIT,
                    summary="Number of nodes not in target state: 2 (warn/crit at 1/2)",
                ),
                Metric("oracle_number_of_nodes_not_in_target_state", 2.0, levels=(1.0, 2.0)),
                Result(
                    state=State.OK,
                    summary="on ezszds8q: offline, target state online; on ezszds9q: offline, target state online",
                ),
            ],
            id="Both of the nodes are offline. Their target state is online, so the state is CRIT.",
        ),
    ],
)
def test_check_oracle_crs_res(
    item: str,
    string_table: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_oracle_crs_res(
                item,
                _DEFAULT_PARAMETERS_ORACLE_CRS_RES,
                parse_oracle_crs_res(string_table),
            )
        )
        == expected_check_result
    )
