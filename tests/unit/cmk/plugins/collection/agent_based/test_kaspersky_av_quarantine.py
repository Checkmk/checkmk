#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.collection.agent_based.kaspersky_av_quarantine import (
    check_kaspersky_av_quarantine,
    Section,
)


@pytest.mark.parametrize(
    "section,expected_results",
    [
        (
            {"Objects": " 1", "Last added": " unkown"},
            [
                Result(state=State.CRIT, summary="1 Objects in Quarantine, Last added: unkown"),
                Metric(name="Objects", value=1.0),
            ],
        )
    ],
)
def test_check_kaskpersky_av_client(section: Section, expected_results: CheckResult) -> None:
    assert list(check_kaspersky_av_quarantine(section)) == expected_results
