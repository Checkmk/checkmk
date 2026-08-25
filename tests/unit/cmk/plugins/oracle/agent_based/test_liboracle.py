#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.oracle.agent_based.liboracle import oracle_handle_ora_errors


def test_failure_row_with_an_ora_message() -> None:
    line = ["orcl", "FAILURE", "ORA-00942: table or view does not exist"]
    assert oracle_handle_ora_errors(line) == "ORA-00942: table or view does not exist"


def test_failure_row_with_a_non_ora_message() -> None:
    line = ["orcl", "FAILURE", "IO Error: The Network Adapter could not establish the connection"]
    assert (
        oracle_handle_ora_errors(line)
        == "IO Error: The Network Adapter could not establish the connection"
    )


def test_legacy_failure_row_whose_message_contains_the_separator() -> None:
    line = ["orcl", "FAILURE", "ORA-00600: internal error [x", "y]"]
    assert oracle_handle_ora_errors(line) == "ORA-00600: internal error [x y]"


def test_failure_row_with_an_empty_message() -> None:
    line = ["orcl", "FAILURE", ""]
    assert oracle_handle_ora_errors(line) is False


def test_failure_row_with_a_whitespace_message() -> None:
    line = ["orcl", "FAILURE", "   "]
    assert oracle_handle_ora_errors(line) is False


def test_bare_failure_marker_without_a_message() -> None:
    line = ["orcl", "FAILURE"]
    assert oracle_handle_ora_errors(line) is False


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
    assert oracle_handle_ora_errors(line) is None


def test_legacy_error_row_starting_with_ora() -> None:
    line = ["ORA-01017:", "invalid", "username/password"]
    assert (
        oracle_handle_ora_errors(line)
        == 'Found error in agent output "ORA-01017: invalid username/password"'
    )


def test_legacy_error_row_with_ora_in_the_second_field() -> None:
    line = ["orcl", "ORA-01017:", "invalid username/password"]
    assert (
        oracle_handle_ora_errors(line)
        == 'Found error in agent output "ORA-01017: invalid username/password"'
    )


def test_error_row_from_the_1_6_solaris_agent_sup_9521() -> None:
    line = ["Error", "ORA-01017: invalid username/password"]
    assert (
        oracle_handle_ora_errors(line)
        == 'Found error in agent output "ORA-01017: invalid username/password"'
    )


def test_echoed_sql_statement_before_an_error_message() -> None:
    line = ["orcl", "select", "*", "from", "v$instance"]
    assert oracle_handle_ora_errors(line) is False


def test_single_field_row() -> None:
    line = ["single-field-row"]
    assert oracle_handle_ora_errors(line) is None


def test_regular_data_row() -> None:
    line = ["orcl", "97", "322", "105"]
    assert oracle_handle_ora_errors(line) is None
