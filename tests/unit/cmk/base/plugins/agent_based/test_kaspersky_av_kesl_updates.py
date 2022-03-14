#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import set_timezone

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kaspersky_av_kesl_updates import check_kaspersky_av_kesl_updates


@pytest.fixture(scope="module", autouse=True)
def set_fixed_timezone():
    with set_timezone("UTC"):
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
                Result(state=State.OK, summary="Database date: Jan 01 1970 00:00:00"),
                Result(state=State.OK, summary="Database records: 1"),
            ],
        ),
    ],
)
def test_check_kaskpersky_av_client(section, results):
    assert list(check_kaspersky_av_kesl_updates(section)) == results
