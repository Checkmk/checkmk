#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import set_timezone

import cmk.base.plugins.agent_based.kaspersky_av_client as kaspersky_av_client
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture(scope="module", autouse=True)
def set_fixed_timezone():
    with set_timezone("UTC"):
        yield


@pytest.mark.parametrize(
    "string_table,now,expected_section",
    [
        (
            [["Fullscan", "01.01.1970", "00:00:00", "1"]],
            1,
            dict(fullscan_age=1, fullscan_failed=True),
        ),
        ([["Signatures", "01.01.1970", "00:00:00"]], 1, dict(signature_age=1)),
        ([["Signatures", "01.01.1970"]], 1, dict(signature_age=1)),
        ([["Signatures", "Missing"]], 0, {}),
    ],
)
def test_parse_kaspersky_av_client(string_table, now, expected_section):
    assert kaspersky_av_client._parse_kaspersky_av_client(string_table, now=now) == expected_section


@pytest.mark.parametrize(
    "section,results",
    [
        (
            dict(fullscan_age=2, signature_age=2),
            [
                Result(
                    state=State.WARN,
                    summary="Last update of signatures: 2 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
                Result(
                    state=State.WARN,
                    summary="Last fullscan: 2 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
            ],
        ),
        (
            dict(fullscan_age=3, signature_age=3),
            [
                Result(
                    state=State.CRIT,
                    summary="Last update of signatures: 3 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
                Result(
                    state=State.CRIT,
                    summary="Last fullscan: 3 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
            ],
        ),
        (
            dict(fullscan_failed=True, fullscan_age=1, signature_age=1),
            [
                Result(state=State.OK, summary="Last update of signatures: 1 second ago"),
                Result(state=State.OK, summary="Last fullscan: 1 second ago"),
                Result(state=State.CRIT, summary="Last fullscan failed"),
            ],
        ),
        (
            {},
            [
                Result(state=State.UNKNOWN, summary="Last update of signatures unkown"),
                Result(state=State.UNKNOWN, summary="Last fullscan unkown"),
            ],
        ),
    ],
)
def test_check_kaskpersky_av_client(section, results):
    test_params = dict(signature_age=(2.0, 3.0), fullscan_age=(2.0, 3.0))
    assert list(kaspersky_av_client.check_kaspersky_av_client(test_params, section)) == results
