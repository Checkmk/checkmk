#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import assertCheckResultsEqual, CheckResult

pytestmark = pytest.mark.checks


def _get_from_context(name, context={}):  # pylint: disable=dangerous-default-value
    if not context:
        context.update(Check("nullmailer_mailq").context)
    return context[name]


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
def test_parse_function(info, expected_parsed) -> None:
    parse_nullmailer_mailq = _get_from_context("parse_nullmailer_mailq")
    queue = _get_from_context("Queue")
    assert parse_nullmailer_mailq(info) == [queue(*p) for p in expected_parsed]


@pytest.mark.parametrize(
    "raw_queue, levels_length, expected_result",
    [
        (
            (25, 0, "deferred"),
            (10, 20),
            [
                (0, "Deferred: 0 mails", [("length", 0, 10, 20)]),
                (0, "Size: 25 B", [("size", 25)]),
            ],
        ),
        (
            (25, 12, "deferred"),
            (10, 20),
            [
                (
                    1,
                    "Deferred: 12 mails (warn/crit at 10 mails/20 mails)",
                    [("length", 12, 10, 20)],
                ),
                (0, "Size: 25 B", [("size", 25)]),
            ],
        ),
        # Other queues have no metrics:
        (
            (1024, 123, "Other queue"),
            (10, 20),
            [
                (2, "Other queue: 123 mails (warn/crit at 10 mails/20 mails)"),
                (0, "Size: 1.00 KiB"),
            ],
        ),
    ],
)
def test_check_single_queue(raw_queue, levels_length, expected_result) -> None:
    check_single_queue = _get_from_context("_check_single_queue")
    queue = _get_from_context("Queue")
    assertCheckResultsEqual(
        CheckResult(check_single_queue(queue(*raw_queue), levels_length)),
        CheckResult(expected_result),
    )


@pytest.mark.parametrize(
    "raw_queues, expected_result",
    [
        (
            [(25, 0, "deferred"), (25, 0, "failed")],
            [
                (0, "Deferred: 0 mails", [("length", 0, 10, 20)]),
                (0, "Size: 25 B", [("size", 25)]),
                (0, "Failed: 0 mails", []),
                (0, "Size: 25 B", []),
            ],
        ),
    ],
)
def test_check_nullmailer_mailq(raw_queues, expected_result) -> None:
    dummy_item = ""
    params = _get_from_context("nullmailer_mailq_default_levels")
    check_nullmailer_mailq = _get_from_context("check_nullmailer_mailq")
    queue = _get_from_context("Queue")
    assertCheckResultsEqual(
        CheckResult(
            check_nullmailer_mailq(
                dummy_item, params, [queue(*raw_queue) for raw_queue in raw_queues]
            )
        ),
        CheckResult(expected_result),
    )
