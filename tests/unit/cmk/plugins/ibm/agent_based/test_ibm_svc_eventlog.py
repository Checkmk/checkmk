#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ibm.agent_based.ibm_svc_eventlog import (
    check_ibm_svc_eventlog,
    discover_ibm_svc_eventlog,
    parse_ibm_svc_eventlog,
)

_STRING_TABLE_WITH_MESSAGES = [
    [
        "588",
        "120404112526",
        "mdiskgrp",
        "6",
        "md07_sas10k",
        "",
        "alert",
        "no",
        "989001",
        "",
        "Managed Disk Group space warning",
    ],
    [
        "589",
        "120404112851",
        "mdiskgrp",
        "7",
        "md08_nlsas7k_1t",
        "",
        "alert",
        "no",
        "989001",
        "",
        "Managed Disk Group space warning",
    ],
    [
        "590",
        "120404112931",
        "mdiskgrp",
        "8",
        "md09_nlsas7k_1t",
        "",
        "alert",
        "no",
        "989001",
        "",
        "Last error message",
    ],
]

_STRING_TABLE_ONE_MESSAGE = [
    [
        "164",
        "220522214408",
        "enclosure",
        "1",
        "",
        "",
        "alert",
        "no",
        "085044",
        "1114",
        "Enclosure Battery fault type 1",
        "",
        "",
    ],
]

_STRING_TABLE_EMPTY: list[list[str]] = []


def test_discover_ibm_svc_eventlog_with_messages() -> None:
    assert list(discover_ibm_svc_eventlog(parse_ibm_svc_eventlog(_STRING_TABLE_WITH_MESSAGES))) == [
        Service()
    ]


def test_discover_ibm_svc_eventlog_empty() -> None:
    assert list(discover_ibm_svc_eventlog(parse_ibm_svc_eventlog(_STRING_TABLE_EMPTY))) == [
        Service()
    ]


def test_check_ibm_svc_eventlog_no_messages() -> None:
    result = list(check_ibm_svc_eventlog(parse_ibm_svc_eventlog(_STRING_TABLE_EMPTY)))
    assert result == [
        Result(
            state=State.OK,
            summary="No messages not expired and not yet fixed found in event log",
        )
    ]


def test_check_ibm_svc_eventlog_one_message() -> None:
    result = list(check_ibm_svc_eventlog(parse_ibm_svc_eventlog(_STRING_TABLE_ONE_MESSAGE)))
    assert result == [
        Result(
            state=State.WARN,
            summary="1 messages not expired and not yet fixed found in event log, last was: Enclosure Battery fault type 1",
        )
    ]


def test_check_ibm_svc_eventlog_multiple_messages() -> None:
    result = list(check_ibm_svc_eventlog(parse_ibm_svc_eventlog(_STRING_TABLE_WITH_MESSAGES)))
    assert result == [
        Result(
            state=State.WARN,
            summary="3 messages not expired and not yet fixed found in event log, last was: Last error message",
        )
    ]
