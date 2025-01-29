#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.collection.agent_based.mongodb_replica import (
    check_mongodb_replica,
    parse_mongodb_replica,
    ReplicaSet,
    Secondaries,
)


@pytest.mark.parametrize(
    "string_table, parsed_section",
    [
        pytest.param(
            [
                [
                    '{"primary": "idbv0068.xyz.de:27017", "secondaries": {"active": '
                    '["idbv0067.xyz:27017", "idbv0068.xyz.de:27017"], "passive": '
                    '["idbv0070.xyz:27017", "idbv0071.xyz.de:27017"]}, "arbiters": '
                    '["idbv0069.xyz.de:27017"]}'
                ]
            ],
            ReplicaSet(
                primary="idbv0068.xyz.de:27017",
                secondaries=Secondaries(
                    active=[
                        "idbv0067.xyz:27017",
                        "idbv0068.xyz.de:27017",
                    ],
                    passive=[
                        "idbv0070.xyz:27017",
                        "idbv0071.xyz.de:27017",
                    ],
                ),
                arbiters=["idbv0069.xyz.de:27017"],
            ),
            id="up-to-date case",
        ),
        pytest.param(
            [['{"primary": null, "secondaries": {"active": [], "passive": []}, "arbiters": []}']],
            ReplicaSet(
                primary=None,
                secondaries=Secondaries(
                    active=[],
                    passive=[],
                ),
                arbiters=[],
            ),
            id="everything missing",
        ),
        pytest.param(
            [
                [
                    "primary",
                    "idbv0068.xyz.de:27017",
                ],
                [
                    "hosts",
                    "idbv0067.xyz:27017 idbv0068.xyz.de:27017",
                ],
                [
                    "arbiters",
                    "idbv0069.xyz.de:27017",
                ],
            ],
            ReplicaSet(
                primary="idbv0068.xyz.de:27017",
                secondaries=Secondaries(
                    active=[
                        "idbv0067.xyz:27017",
                        "idbv0068.xyz.de:27017",
                    ],
                    passive=[],
                ),
                arbiters=["idbv0069.xyz.de:27017"],
            ),
            id="legacy case",
        ),
    ],
)
def test_parse_mongodb_replica(
    string_table: StringTable,
    parsed_section: ReplicaSet,
) -> None:
    assert parse_mongodb_replica(string_table) == parsed_section


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            ReplicaSet(
                primary="idbv0068.xyz.de:27017",
                secondaries=Secondaries(
                    active=[
                        "idbv0067.xyz:27017",
                        "idbv0068.xyz.de:27017",
                    ],
                    passive=[
                        "idbv0070.xyz:27017",
                        "idbv0071.xyz.de:27017",
                    ],
                ),
                arbiters=["idbv0069.xyz.de:27017"],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Primary: idbv0068.xyz.de:27017",
                ),
                Result(
                    state=State.OK,
                    summary="Active secondaries: idbv0067.xyz:27017, idbv0068.xyz.de:27017",
                ),
                Result(
                    state=State.OK,
                    summary="Passive secondaries: idbv0070.xyz:27017, idbv0071.xyz.de:27017",
                ),
                Result(
                    state=State.OK,
                    summary="Arbiters: idbv0069.xyz.de:27017",
                ),
            ],
            id="primary present",
        ),
        pytest.param(
            ReplicaSet(
                primary=None,
                secondaries=Secondaries(
                    active=[
                        "idbv0067.xyz:27017",
                        "idbv0068.xyz.de:27017",
                    ],
                    passive=[],
                ),
                arbiters=["idbv0069.xyz.de:27017"],
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="Replica set does not have a primary node",
                ),
                Result(
                    state=State.OK,
                    summary="Active secondaries: idbv0067.xyz:27017, idbv0068.xyz.de:27017",
                ),
                Result(
                    state=State.OK,
                    summary="No passive secondaries",
                ),
                Result(
                    state=State.OK,
                    summary="Arbiters: idbv0069.xyz.de:27017",
                ),
            ],
            id="primary missing",
        ),
        pytest.param(
            ReplicaSet(
                primary=None,
                secondaries=Secondaries(
                    active=[],
                    passive=[],
                ),
                arbiters=[],
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="Replica set does not have a primary node",
                ),
                Result(
                    state=State.OK,
                    summary="No active secondaries",
                ),
                Result(
                    state=State.OK,
                    summary="No passive secondaries",
                ),
                Result(
                    state=State.OK,
                    summary="No arbiters",
                ),
            ],
            id="everything missing",
        ),
        pytest.param(
            ReplicaSet(
                primary="idbv0068.xyz.de:27017",
                secondaries=Secondaries(
                    active=[],
                    passive=[],
                ),
                arbiters=[],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Primary: idbv0068.xyz.de:27017",
                ),
                Result(
                    state=State.OK,
                    summary="No active secondaries",
                ),
                Result(
                    state=State.OK,
                    summary="No passive secondaries",
                ),
                Result(
                    state=State.OK,
                    summary="No arbiters",
                ),
            ],
            id="minimal case",
        ),
    ],
)
def test_check_mongodb_replica(
    section: ReplicaSet,
    expected_check_result: Sequence[Result],
) -> None:
    assert list(check_mongodb_replica(section=section)) == expected_check_result
