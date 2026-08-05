#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.qmail_stats.agent_based.qmail_stats import (
    check_qmail_stats,
    parse_qmail_stats,
    Queue,
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [
                ["messages", "in", "queue:", "0"],
                ["messages", "in", "queue", "but", "not", "yet", "preprocessed:", "0"],
            ],
            Queue(0),
            id="empty queue",
        ),
        pytest.param(
            [
                ["messages", "in", "queue:", "32"],
                ["messages", "in", "queue", "but", "not", "yet", "preprocessed:", "1"],
            ],
            Queue(32),
            id="non-empty queue",
        ),
        pytest.param([], None, id="no data"),
        pytest.param([[]], None, id="empty line"),
        pytest.param(
            [["qmail-qstat:", "fatal:", "unable", "to", "chdir"]],
            None,
            id="unparsable output",
        ),
    ],
)
def test_parse_qmail_stats(string_table: StringTable, expected: Queue | None) -> None:
    assert parse_qmail_stats(string_table) == expected


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            Queue(5),
            [
                Result(state=State.OK, summary="Deferred mails: 5"),
                Metric("queue", 5.0, levels=(10.0, 20.0)),
            ],
            id="below levels",
        ),
        pytest.param(
            Queue(15),
            [
                Result(state=State.WARN, summary="Deferred mails: 15 (warn/crit at 10/20)"),
                Metric("queue", 15.0, levels=(10.0, 20.0)),
            ],
            id="warn",
        ),
        pytest.param(
            Queue(32),
            [
                Result(state=State.CRIT, summary="Deferred mails: 32 (warn/crit at 10/20)"),
                Metric("queue", 32.0, levels=(10.0, 20.0)),
            ],
            id="crit",
        ),
    ],
)
def test_check_qmail_stats(section: Queue, expected_result: Sequence[Result | Metric]) -> None:
    assert list(check_qmail_stats({"deferred": (10, 20)}, section)) == expected_result
