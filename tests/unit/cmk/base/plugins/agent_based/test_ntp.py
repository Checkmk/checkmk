#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest import mock

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.ntp import (
    _ntp_fmt_time,
    check_ntp,
    check_ntp_summary,
    parse_ntp,
    Peer,
    Section,
)


def test_check_ntp() -> None:
    section: Section = {
        "42.202.61.100": Peer("-", "42.202.61.100", ".INIT.", 16, _ntp_fmt_time("-"), "0", 0.0, 0.0)
    }
    assert list(check_ntp("item", {}, section)) == []


def test_check_ntp_summanry() -> None:
    section: Section = {}
    assert list(check_ntp_summary({}, section)) == [
        Result(state=State.OK, summary="Time since last sync: N/A (started monitoring)")
    ]


@mock.patch(
    "cmk.base.plugins.agent_based.ntp.get_value_store",
    mock.Mock(return_value={"time_server": 1570001652.37}),
)
def test_check_ntp_timeserver_stored() -> None:
    server_time = 1569922392.37 + 60 * 60 * 22 + 60, "UTC"

    section: Section = {}
    with on_time(*server_time):
        assert list(check_ntp_summary({}, section)) == [
            Result(state=State.OK, summary="Time since last sync: 0 seconds")
        ]


def test_parse_ntp() -> None:
    assert parse_ntp(
        [
            [
                "%",
                "remote",
                "refid",
                "st",
                "t",
                "when",
                "poll",
                "reach",
                "delay",
                "offset",
                "jitter",
            ],
            ["=", "============================================================================="],
            ["+", "127.0.0.1", ".PTB.", "1", "u", "72", "256", "377", "16.199", "0.623", "1.533"],
            ["*", "127.0.0.2", ".PTB.", "1", "u", "92", "256", "377", "15.515", "0.587", "1.439"],
            ["+", "127.0.0.3", ".PTB.", "1", "u", "230", "256", "377", "15.837", "0.490", "1.035"],
        ]
    ) == {
        "127.0.0.1": Peer(
            statecode="+",
            name="127.0.0.1",
            refid=".PTB.",
            stratum=1,
            when=72,
            reach="377",
            offset=0.623,
            jitter=1.533,
        ),
        "127.0.0.2": Peer(
            statecode="*",
            name="127.0.0.2",
            refid=".PTB.",
            stratum=1,
            when=92,
            reach="377",
            offset=0.587,
            jitter=1.439,
        ),
        None: Peer(
            statecode="*",
            name="127.0.0.2",
            refid=".PTB.",
            stratum=1,
            when=92,
            reach="377",
            offset=0.587,
            jitter=1.439,
        ),
        "127.0.0.3": Peer(
            statecode="+",
            name="127.0.0.3",
            refid=".PTB.",
            stratum=1,
            when=230,
            reach="377",
            offset=0.49,
            jitter=1.035,
        ),
    }
