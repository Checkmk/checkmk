#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kaspersky_av_kesl_updates import (
    check_kaspersky_av_kesl_updates,
    Section,
)


@pytest.fixture(scope="module", autouse=True)
def set_fixed_timezone():
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))):
        yield


@pytest.mark.parametrize(
    "section,results",
    [
        (
            {
                "Anti-virus databases loaded": "No",
                "Last release date of databases": "1970-01-01 00:00:00",
                "Anti-virus database records": "1",
            },
            [
                Result(state=State.CRIT, summary="Databases loaded: False"),
                Result(state=State.OK, summary="Database date: 1970-01-01 00:00:00"),
                Result(state=State.OK, summary="Database records: 1"),
            ],
        ),
    ],
)
def test_check_kaskpersky_av_client(section: Section, results: Sequence[Result]) -> None:
    assert list(check_kaspersky_av_kesl_updates(section)) == results
