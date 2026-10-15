#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History file backend"""

import datetime
import logging
import shlex
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config
from cmk.ec.history import _current_history_period
from cmk.ec.history_file import (
    _grep_pipeline,
    convert_history_line,
    FileHistory,
    parse_history_file,
)
from cmk.ec.main import StatusTableHistory
from cmk.ec.query import QueryFilter, QueryGET, StatusTable


def test_file_add_get(history: FileHistory) -> None:
    """Add 2 documents to history, get filtered result with 1 document."""

    event1 = ec.Event(host=HostName("ABC1"), text="Event1 text", core_host=HostName("ABC"))
    event2 = ec.Event(host=HostName("ABC2"), text="Event2 text", core_host=HostName("ABC"))

    history.add(event=event1, what="NEW")
    history.add(event=event2, what="NEW")

    logger = logging.getLogger("cmk.mkeventd")

    def get_table(name: str) -> StatusTable:
        assert name == "history"
        return StatusTableHistory(logger, history)

    query = QueryGET(
        get_table,
        ["GET history", "Columns: history_what host_name", "Filter: event_host = ABC1"],
        logger,
    )

    query_result = history.get(query)

    (row,) = query_result
    column_index = get_table("history").column_names.index
    assert row[column_index("history_what")] == "NEW"
    assert row[column_index("event_host")] == "ABC1"


# fmt: off
@pytest.mark.parametrize(
    "operator_name, argument, expected_texts",
    [
        pytest.param("!=",  "disk full", {"Disk full", "CPU load high"}, id="not equal"),
        pytest.param("!=~", "disk full", {"CPU load high"},              id="not equal ignoring case"),
        pytest.param("!~",  "disk",      {"Disk full", "CPU load high"}, id="regex does not match"),
        pytest.param("!~~", "disk",      {"CPU load high"},              id="regex does not match ignoring case"),
    ],
)
# fmt: on
def test_negated_filter_ignores_matches_in_other_columns(
    history: FileHistory, operator_name: str, argument: str, expected_texts: set[str]
) -> None:
    history.add(event=ec.Event(text="Disk full"), what="NEW")
    history.add(event=ec.Event(text="disk full"), what="NEW")
    history.add(event=ec.Event(text="CPU load high", comment="disk full"), what="NEW")
    logger = logging.getLogger("cmk.mkeventd")
    table = StatusTableHistory(logger, history)
    query = QueryGET(
        lambda _name: table,
        ["GET history", "Columns: event_text", f"Filter: event_text {operator_name} {argument}"],
        logger,
    )

    _header, *rows = table.query(query)

    assert {text for (text,) in rows} == expected_texts


# fmt: off
@pytest.mark.parametrize(
    "operator_name, argument, expected_texts",
    [
        pytest.param("~",  "load",          {"CPU load high"},   id="plain string"),
        pytest.param("~~", "LOAD",          {"CPU load high"},   id="plain string, ignoring case"),
        pytest.param("~",  "Event.17",      {"Event 17"},        id="dot"),
        pytest.param("~~", "EVENT.17",      {"Event 17"},        id="dot, ignoring case"),
        pytest.param("~",  r"www\.example", {"www.example.com"}, id="escaped dot"),
        pytest.param("~",  "^disk",         {"disk full"},       id="anchored at the start of the value"),
        pytest.param("~",  "full$",         {"disk full"},       id="anchored at the end of the value"),
        pytest.param("~~", "^DISK",         {"disk full"},       id="anchored, ignoring case"),
        pytest.param("~",  r"\d",           {"Event 17"},        id="escape unknown to grep"),
        pytest.param("~",  "(?i)cpu",       {"CPU load high"},   id="inline flag unknown to grep"),
    ],
)
# fmt: on
def test_regex_filter_selects_all_history_entries_whose_value_matches(
    history: FileHistory, operator_name: str, argument: str, expected_texts: set[str]
) -> None:
    for text in ("disk full", "Event 17", "CPU load high", "www.example.com"):
        history.add(event=ec.Event(text=text), what="NEW")
    logger = logging.getLogger("cmk.mkeventd")
    table = StatusTableHistory(logger, history)
    query = QueryGET(
        lambda _name: table,
        ["GET history", "Columns: event_text", f"Filter: event_text {operator_name} {argument}"],
        logger,
    )

    _header, *rows = table.query(query)

    assert {text for (text,) in rows} == expected_texts


def test_current_history_period(config: Config) -> None:
    """timestamp of the beginning of the current history period correctly returned."""
    with time_machine.travel(datetime.datetime.fromtimestamp(1550000000.0, tz=ZoneInfo("CET"))):
        assert _current_history_period(config=config) == 1549929600

    with time_machine.travel(datetime.datetime.fromtimestamp(1550000000.0, tz=ZoneInfo("CET"))):
        assert _current_history_period(config=config | {"history_rotation": "weekly"}) == 1549843200


def test_convert_history_line() -> None:
    """History convert values."""
    values: list[Any] = (
        "1	1666942292.5	DELETE	cmkadmin		5	1	some text	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					rule	heute	0	".split(
            "\t"
        )
    )
    assert len(values) == 30

    convert_history_line(StatusTableHistory.columns, values)

    assert values[0] == 1
    assert values[1] == 1666942292.5
    assert values[5] == 5
    assert values[23] is None
    assert values[24] == ""
    assert values[25] == ""
    assert values[26] == "rule"
    assert values[27] == "heute"
    assert values[28] is False
    assert values[29] == ()


def test_convert_history_line_legacy() -> None:
    """History convert values."""
    values: list[Any] = (
        "1	1666942299	DELETE	cmkadmin		5	1	some text	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin	".split(
            "\t"
        )
    )
    assert len(values) == 23

    convert_history_line(StatusTableHistory.columns, values)

    assert values[0] == 1
    assert values[1] == 1666942299
    assert values[5] == 5
    assert values[23] is None
    assert values[24] == ""
    assert values[25] == ""
    assert values[26] == "host"
    assert values[27] == ""
    assert values[28] is False
    assert values[29] == ""


def test_history_parse(tmp_path: Path) -> None:
    """History parse file"""
    values = """1666942211.07616	NEW			1002	1	999: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942208.0	1666942208.0		0	heute		OMD	0	6	9	asdf	0	open						host	heute	0	
1666942292.2998602	DELETE	cmkadmin		5	1	4: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.2999856	DELETE	cmkadmin		6	1	5: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.3000507	DELETE	cmkadmin		7	1	6: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
    """
    path = tmp_path / "history_test.log"
    path.write_text(values)
    filter_ = QueryFilter(
        column_name="event_id",
        operator_name="=",
        predicate=lambda _: True,
        argument="1",
    )
    tac = f"nl -b a {shlex.quote(str(path))} | tac"
    cmd = " | ".join([tac] + _grep_pipeline([filter_]))

    new_entries = parse_history_file(
        StatusTableHistory.columns,
        path,
        lambda _: True,
        cmd,
        None,
        logging.getLogger("cmk.mkeventd"),
    )

    assert len(new_entries) == 4
    assert new_entries[0][1] == 1666942292.3000507
