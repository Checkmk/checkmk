#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence

import pytest

from cmk.base.plugins.agent_based import zpool_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.zpool_status import Section


@pytest.mark.parametrize("string_table, expected_result", [([], None)])
def test_zpool_status_parse(string_table: StringTable, expected_result: Optional[Section]) -> None:
    section = zpool_status.parse_zpool_status(string_table)
    assert section == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (None, []),
        (Section(message="No pools available"), []),
        (Section(message="All pools are healthy"), [Service()]),
    ],
)
def test_zpool_status_discover(section: Section, expected_result: Sequence[Service]) -> None:
    services = list(zpool_status.discover_zpool_status(section))
    assert services == expected_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [
                ["all", "pools", "are", "healthy"],
            ],
            Result(state=State.OK, summary="All pools are healthy"),
        ),
        (
            [
                ["c0t5000C5004176685Fd0", "ONLINE", "0", "0", "0"],
                ["spare-4", "FAULTED", "0", "0", "0"],
                ["c0t5000C500417668A3d0", "FAULTED", "0", "0", "0", "too", "many", "errors"],
            ],
            Result(state=State.OK, summary="No critical errors"),
        ),
        (
            [
                ["state:", "ONLINE"],
                ["state:", "DEGRADED"],
                ["state:", "UNKNOWN"],
            ],
            Result(state=State.WARN, summary="DEGRADED State, Unknown State"),
        ),
        (
            [
                ["state:", "FAULTED"],
                ["state:", "UNAVIL"],
                ["state:", "REMOVED"],
            ],
            Result(state=State.CRIT, summary="FAULTED State, UNAVIL State, REMOVED State"),
        ),
        (
            [
                ["pool:", "test"],
                ["state:", "ONLINE"],
                [
                    "status:",
                    "One",
                    "or",
                    "more",
                    "devices",
                    "has",
                    "experienced",
                    "an",
                    "unrecoverable",
                    "error.",
                ],
                ["Applications", "are", "unaffected."],
                ["pool:", "test2"],
                [
                    "status:",
                    "One",
                    "or",
                    "more",
                    "devices",
                    "has",
                    "experienced",
                    "an",
                    "unrecoverable",
                    "error.",
                ],
            ],
            Result(
                state=State.WARN,
                summary="test: One or more devices has experienced an unrecoverable error. Applications are unaffected., test2: One or more devices has experienced an unrecoverable error.",
            ),
        ),
        (
            [
                ["state:", "DEGRADED"],
                ["state:", "OFFLINE"],
            ],
            Result(state=State.OK, summary="DEGRADED State"),
        ),
        (
            [
                ["NAME", "STATE", "READ", "WRITE", "CKSUM"],
                ["snapshots", "OFFLINE", "0", "0", "0"],
                ["raidz1", "ONLINE", "0", "0", "0"],
            ],
            Result(state=State.CRIT, summary="snapshots state: OFFLINE"),
        ),
        (
            [
                ["config:"],
                ["NAME", "STATE", "READ", "WRITE", "CKSUM"],
                ["snapshots", "ONLINE", "0", "0", "0"],
                ["raidz1", "ONLINE", "0", "0", "1"],
                ["spares", "OFFLINE", "0", "0", "0"],
            ],
            Result(state=State.WARN, summary="raidz1 CKSUM: 1"),
        ),
        (
            [
                ["config:"],
                ["NAME", "STATE", "READ", "WRITE", "CKSUM"],
                ["snapshots", "ONLINE", "0", "0", "0"],
                ["raidz1", "ONLINE", "0", "0", "a"],
                ["spares", "OFFLINE", "0", "0", "0"],
            ],
            Result(state=State.OK, summary="No critical errors"),
        ),
        (
            [
                ["pool:", "test3"],
                ["errors:", "Device", "experienced", "an", "error."],
            ],
            Result(state=State.WARN, summary="test3: Device experienced an error."),
        ),
    ],
)
def test_zpool_status_check(string_table, expected_result):
    section = zpool_status.parse_zpool_status(string_table)
    assert section
    assert list(zpool_status.check_zpool_status({}, section)) == [expected_result]
