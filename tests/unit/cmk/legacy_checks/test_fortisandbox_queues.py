#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.fortisandbox_queues import (
    check_fortisandbox_queues,
    discover_fortisandbox_queues,
    parse_fortisandbox_queues,
)

_STRING_TABLE = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]]


def test_parse_fortisandbox_queues() -> None:
    assert parse_fortisandbox_queues(_STRING_TABLE) == {
        "Executable": 1,
        "PDF": 2,
        "Office": 3,
        "Flash": 4,
        "Web": 5,
        "Android": 6,
        "MAC": 7,
        "URL job": 8,
        "User defined": 9,
        "Non Sandboxing": 10,
        "Job Queue Assignment": 11,
    }


def test_parse_fortisandbox_queues_empty() -> None:
    assert parse_fortisandbox_queues([]) is None


def test_discover_fortisandbox_queues() -> None:
    assert list(discover_fortisandbox_queues({"PDF": 2, "Office": 3})) == [
        Service(item="PDF"),
        Service(item="Office"),
    ]


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Queue length: 3"),
                Metric("queue", 3.0),
            ],
            id="no levels",
        ),
        pytest.param(
            {"length": (2, 5)},
            [
                Result(state=State.WARN, summary="Queue length: 3 (warn/crit at 2/5)"),
                Metric("queue", 3.0, levels=(2.0, 5.0)),
            ],
            id="warn",
        ),
    ],
)
def test_check_fortisandbox_queues(
    params: Mapping[str, object], expected: Sequence[object]
) -> None:
    assert list(check_fortisandbox_queues("Office", params, {"Office": 3})) == expected


def test_check_fortisandbox_queues_missing_item() -> None:
    assert not list(check_fortisandbox_queues("Office", {}, {"PDF": 2}))
