#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.oracle.agent_based.liboracle import classify_line


def test_failure_row_with_an_ora_message() -> None:
    line = ["orcl", "FAILURE", "ORA-00942: table or view does not exist"]
    assert classify_line(line) == "ORA-00942: table or view does not exist"


def test_failure_row_with_a_non_ora_message() -> None:
    line = ["orcl", "FAILURE", "IO Error: The Network Adapter could not establish the connection"]
    assert classify_line(line) == "IO Error: The Network Adapter could not establish the connection"


def test_failure_row_with_an_empty_message() -> None:
    line = ["orcl", "FAILURE", ""]
    assert classify_line(line) is False


def test_failure_row_with_a_whitespace_message() -> None:
    line = ["orcl", "FAILURE", "   "]
    assert classify_line(line) is False


def test_bare_failure_marker_without_a_message() -> None:
    line = ["orcl", "FAILURE"]
    assert classify_line(line) is False


def test_oracle_jobs_data_row_for_a_pdb_named_failure() -> None:
    line = [
        "DB19",
        "FAILURE",
        "SYS",
        "JOB1",
        "SCHEDULED",
        "0",
        "46",
        "TRUE",
        "15-JUN-21 01.01.01.143871 AM +00:00",
        "-",
        "SUCCEEDED",
    ]
    assert classify_line(line) is None


def test_legacy_error_row_starting_with_ora() -> None:
    line = ["ORA-01017:", "invalid", "username/password"]
    assert (
        classify_line(line) == 'Found error in agent output "ORA-01017: invalid username/password"'
    )


def test_empty_row_is_noise() -> None:
    assert classify_line([]) is False


def test_single_field_row() -> None:
    line = ["single-field-row"]
    assert classify_line(line) is None


def test_regular_data_row() -> None:
    line = ["orcl", "97", "322", "105"]
    assert classify_line(line) is None
