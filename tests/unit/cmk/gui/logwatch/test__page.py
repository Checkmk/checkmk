#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from unittest.mock import patch

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.logwatch._page import get_last_chunk, get_worst_chunk, parse_file

HOST = HostName("myhost")
FILE = "myfile.log"


def _parse(lines: list[str], *, hidecontext: bool = False) -> object:
    with patch("cmk.gui.logwatch._page.get_logfile_lines", return_value=lines):
        return parse_file(None, HOST, FILE, hidecontext=hidecontext, debug=True)


def test_parse_file_returns_none_when_file_missing() -> None:
    with patch("cmk.gui.logwatch._page.get_logfile_lines", return_value=None):
        assert parse_file(None, HOST, FILE, hidecontext=False, debug=True) is None


def test_parse_file_empty_file() -> None:
    assert _parse([]) == []


def test_parse_file_skips_leading_hash_lines() -> None:
    lines = [
        "# hash header line",
        "# another hash line",
        "<<<2024-01-01 12:00:00 WARN>>>",
        "W warning message",
    ]
    result = _parse(lines)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["level"] == 1


def test_parse_file_chunk_levels() -> None:
    lines = [
        "<<<2024-01-01 12:00:00 CRIT>>>",
        "C critical line",
        "<<<2024-01-01 12:01:00 WARN>>>",
        "W warning line",
        "<<<2024-01-01 12:02:00 OK>>>",
        "O ok line",
    ]
    result = _parse(lines)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["level"] == 2  # CRIT
    assert result[1]["level"] == 1  # WARN
    assert result[2]["level"] == 0  # OK


def test_parse_file_line_classification() -> None:
    lines = [
        "<<<2024-01-01 12:00:00 WARN>>>",
        "C critical",
        "W warning",
        "u warning-u",
        "O ok",
        ". context",
    ]
    result = _parse(lines)
    assert isinstance(result, list)
    chunk_lines = result[0]["lines"]
    assert chunk_lines[0] == {"level": 2, "class": "CRIT", "line": "critical"}
    assert chunk_lines[1] == {"level": 1, "class": "WARN", "line": "warning"}
    assert chunk_lines[2] == {"level": 1, "class": "WARN", "line": "warning-u"}
    assert chunk_lines[3] == {"level": 0, "class": "OK", "line": "ok"}
    assert chunk_lines[4] == {"level": 0, "class": "context", "line": "context"}


def test_parse_file_hidecontext_filters_context_lines() -> None:
    lines = [
        "<<<2024-01-01 12:00:00 WARN>>>",
        "W warning",
        ". context line",
    ]
    result_with_context = _parse(lines, hidecontext=False)
    result_hidden = _parse(lines, hidecontext=True)

    assert isinstance(result_with_context, list)
    assert isinstance(result_hidden, list)
    assert len(result_with_context[0]["lines"]) == 2
    assert len(result_hidden[0]["lines"]) == 1
    assert result_hidden[0]["lines"][0]["class"] == "WARN"


def test_parse_file_datetime_parsed() -> None:
    lines = ["<<<2024-06-15 08:30:00 WARN>>>"]
    result = _parse(lines)
    assert isinstance(result, list)
    assert result[0]["datetime"] == datetime.datetime(2024, 6, 15, 8, 30, 0)


def test_get_worst_chunk_picks_highest_level() -> None:
    chunks = [
        {"level": 0, "lines": [{"level": 0}], "datetime": datetime.datetime(2024, 1, 1)},
        {"level": 1, "lines": [{"level": 1}], "datetime": datetime.datetime(2024, 1, 2)},
        {"level": 2, "lines": [{"level": 2}], "datetime": datetime.datetime(2024, 1, 3)},
    ]
    assert get_worst_chunk(chunks) is chunks[2]


def test_get_last_chunk_picks_most_recent() -> None:
    chunks = [
        {"datetime": datetime.datetime(2024, 1, 3), "lines": []},
        {"datetime": datetime.datetime(2024, 1, 1), "lines": []},
        {"datetime": datetime.datetime(2024, 1, 2), "lines": []},
    ]
    assert get_last_chunk(chunks) is chunks[0]


def test_parse_file_debug_reraises_exception() -> None:
    with patch("cmk.gui.logwatch._page.get_logfile_lines", return_value=["<<<bad format>>>"]):
        with pytest.raises(Exception):
            parse_file(None, HOST, FILE, hidecontext=False, debug=True)
