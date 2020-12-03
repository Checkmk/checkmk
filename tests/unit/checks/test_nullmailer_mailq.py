#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check
from checktestlib import assertCheckResultsEqual, CheckResult

pytestmark = pytest.mark.checks


def _get_from_context(name, context={}):  # pylint: disable=dangerous-default-value
    if not context:
        context.update(Check("nullmailer_mailq").context)
    return context[name]


@pytest.mark.parametrize("info, expected_parsed", [
    ([], []),
    ([["25", "0"]], [(25, 0, "deferred")]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_function(info, expected_parsed):
    parse_nullmailer_mailq = _get_from_context("parse_nullmailer_mailq")
    queue = _get_from_context("Queue")
    assert parse_nullmailer_mailq(info) == [queue(*p) for p in expected_parsed]


@pytest.mark.parametrize(
    "raw_queue, levels_length, expected_result",
    [
        ((25, 0, "deferred"), (10, 20), [
            (0, 'Deferred: Length: 0', [('length', 0, 10, 20)]),
            (0, 'Size: 25.00 B', [('size', 25)]),
        ]),
        ((25, 12, "deferred"), (10, 20), [
            (1, 'Deferred: Length: 12 (warn/crit at 10/20)', [('length', 12, 10, 20)]),
            (0, 'Size: 25.00 B', [('size', 25)]),
        ]),
        # Other queues have no metrics:
        ((1024, 123, "Other queue"), (10, 20), [
            (2, 'Other queue: Length: 123 (warn/crit at 10/20)'),
            (0, 'Size: 1.00 kB'),
        ]),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test__check_single_queue(raw_queue, levels_length, expected_result):
    check_single_queue = _get_from_context("_check_single_queue")
    queue = _get_from_context("Queue")
    assertCheckResultsEqual(
        CheckResult(check_single_queue(queue(*raw_queue), levels_length)),
        CheckResult(expected_result),
    )
