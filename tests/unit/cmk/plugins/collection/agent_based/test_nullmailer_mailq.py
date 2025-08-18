#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import LevelsT, Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.nullmailer_mailq import (
    check_nullmailer_mailq,
    check_single_queue,
    NULLMAILER_MAILQ_DEFAULT_LEVELS,
    parse_nullmailer_mailq,
    Queue,
)

pytestmark = pytest.mark.checks


RawQueue = tuple[int, int, str]


@pytest.mark.parametrize(
    "info, expected_parsed",
    [
        ([], []),
        ([["25", "0"]], [(25, 0, "deferred")]),
        (
            [["25", "0", "deferred"], ["25", "0", "failed"]],
            [(25, 0, "deferred"), (25, 0, "failed")],
        ),
    ],
)
def test_parse_function(info: StringTable, expected_parsed: Sequence[RawQueue]) -> None:
    assert parse_nullmailer_mailq(info) == [Queue(*p) for p in expected_parsed]


@pytest.mark.parametrize(
    "raw_queue, levels_length, expected_result",
    [
        (
            (25, 0, "deferred"),
            ("fixed", (10, 20)),
            [
                Result(state=State.OK, summary="Deferred: 0 mails"),
                Metric("length", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Size: 25 B"),
                Metric("size", 25.0),
            ],
        ),
        (
            (25, 12, "deferred"),
            ("fixed", (10, 20)),
            [
                Result(
                    state=State.WARN, summary="Deferred: 12 mails (warn/crit at 10 mails/20 mails)"
                ),
                Metric("length", 12.0, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Size: 25 B"),
                Metric("size", 25.0),
            ],
        ),
        # Other queues have no metrics:
        (
            (1024, 123, "Other queue"),
            ("fixed", (10, 20)),
            [
                Result(
                    state=State.CRIT,
                    summary="Other queue: 123 mails (warn/crit at 10 mails/20 mails)",
                ),
                Result(state=State.OK, summary="Size: 1.00 KiB"),
            ],
        ),
    ],
)
def test_check_single_queue(
    raw_queue: RawQueue,
    levels_length: LevelsT,
    expected_result: Sequence[Metric | Result],
) -> None:
    assert list(check_single_queue(Queue(*raw_queue), levels_length)) == expected_result


@pytest.mark.parametrize(
    "raw_queues, expected_result",
    [
        (
            [(25, 0, "deferred"), (25, 0, "failed")],
            [
                Result(state=State.OK, summary="Deferred: 0 mails"),
                Metric("length", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Size: 25 B"),
                Metric("size", 25.0, levels=(None, None)),
                Result(state=State.OK, summary="Failed: 0 mails"),
                Result(state=State.OK, summary="Size: 25 B"),
            ],
        ),
    ],
)
def test_check_nullmailer_mailq(
    raw_queues: Sequence[RawQueue], expected_result: Sequence[Metric | Result]
) -> None:
    assert (
        list(
            check_nullmailer_mailq(
                NULLMAILER_MAILQ_DEFAULT_LEVELS,
                [Queue(*raw_queue) for raw_queue in raw_queues],
            )
        )
        == expected_result
    )
