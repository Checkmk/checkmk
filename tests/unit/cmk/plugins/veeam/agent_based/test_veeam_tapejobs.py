#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based import veeam_tapejobs


@pytest.fixture(name="string_table")
def fixture_string_table() -> list[list[str]]:
    """Veeam tape backup job information.

    Data format: [JobName, JobID, LastResult, LastState]
    Contains jobs with various states: Success/Warning/Failed results,
    Working/Idle/Stopped states with runtime tracking.
    """
    return [
        ["JobName", "JobID", "LastResult", "LastState"],
        ["Job One", "1", "Success", "Stopped"],
        ["Job Two", "2", "Warning", "Stopped"],
        ["Job Three", "3", "Failed", "Stopped"],
        ["Job Four", "4", "None", "Working"],
        ["Job Five (older)", "5", "None", "Working"],
        ["Job Six", "6", "None", "Idle"],
        ["Job Seven (older)", "7", "None", "Idle"],
    ]


@pytest.fixture(name="parsed_data")
def fixture_parsed_data(
    string_table: list[list[str]],
) -> veeam_tapejobs.Section:
    """Parsed Veeam tape job data with job information."""
    return veeam_tapejobs.parse_veeam_tapejobs(string_table)


def test_parse_veeam_tapejobs(string_table: list[list[str]]) -> None:
    """Test parsing Veeam tape job data with various job states."""
    parsed = veeam_tapejobs.parse_veeam_tapejobs(string_table)

    assert len(parsed) == 7

    # Test completed jobs
    assert parsed["Job One"] == {"job_id": "1", "last_result": "Success", "last_state": "Stopped"}
    assert parsed["Job Two"] == {"job_id": "2", "last_result": "Warning", "last_state": "Stopped"}
    assert parsed["Job Three"] == {"job_id": "3", "last_result": "Failed", "last_state": "Stopped"}

    # Test running jobs
    assert parsed["Job Four"] == {"job_id": "4", "last_result": "None", "last_state": "Working"}
    assert parsed["Job Five (older)"] == {
        "job_id": "5",
        "last_result": "None",
        "last_state": "Working",
    }

    # Test idle jobs
    assert parsed["Job Six"] == {"job_id": "6", "last_result": "None", "last_state": "Idle"}
    assert parsed["Job Seven (older)"] == {
        "job_id": "7",
        "last_result": "None",
        "last_state": "Idle",
    }


def test_parse_veeam_tapejobs_incomplete_lines() -> None:
    """Test parsing with incomplete data lines."""
    string_table = [
        ["JobName", "JobID", "LastResult", "LastState"],
        ["Complete Job", "1", "Success", "Stopped"],
        ["Incomplete"],  # Missing columns
        ["Another Complete", "2", "Failed", "Stopped"],
    ]

    parsed = veeam_tapejobs.parse_veeam_tapejobs(string_table)

    # Should only parse complete lines
    assert len(parsed) == 2
    assert "Complete Job" in parsed
    assert "Another Complete" in parsed
    assert "Incomplete" not in parsed


def test_discover_veeam_tapejobs(parsed_data: veeam_tapejobs.Section) -> None:
    """Test discovery of all Veeam tape backup jobs."""
    assert list(veeam_tapejobs.discover_veeam_tapejobs(parsed_data)) == [
        Service(item="Job One"),
        Service(item="Job Two"),
        Service(item="Job Three"),
        Service(item="Job Four"),
        Service(item="Job Five (older)"),
        Service(item="Job Six"),
        Service(item="Job Seven (older)"),
    ]


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_completed_success(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for successfully completed backup job."""
    value_store: dict[str, object] = {}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job One", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert results == [
        Result(state=State.OK, summary="Last backup result: Success"),
        Result(state=State.OK, summary="Last state: Stopped"),
    ]


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_completed_warning(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for backup job completed with warning."""
    value_store: dict[str, object] = {}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Two", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert results == [
        Result(state=State.WARN, summary="Last backup result: Warning"),
        Result(state=State.OK, summary="Last state: Stopped"),
    ]


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_completed_failed(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for failed backup job."""
    value_store: dict[str, object] = {}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Three", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert results == [
        Result(state=State.CRIT, summary="Last backup result: Failed"),
        Result(state=State.OK, summary="Last state: Stopped"),
    ]


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_working_normal_runtime(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for working job with normal runtime."""
    value_store: dict[str, object] = {"4.running_since": 1562056000}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Four", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert len(results) == 2
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "Backup in progress since" in results[0].summary
    assert "currently working" in results[0].summary

    assert isinstance(results[1], Result)
    assert results[1].state == State.OK
    assert "Running time:" in results[1].summary


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_working_long_runtime(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for working job with excessive runtime."""
    value_store: dict[str, object] = {"5.running_since": 1560006000}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Five (older)", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert len(results) == 2
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "Backup in progress since" in results[0].summary
    assert "currently working" in results[0].summary

    assert isinstance(results[1], Result)
    assert results[1].state == State.CRIT
    assert "Running time:" in results[1].summary
    assert "warn/crit at" in results[1].summary


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_working_warn_runtime(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for working job whose runtime crosses the warning level only."""
    # 1562056877 - 1561956877 == 100000 s, between the 1 day / 2 day levels.
    value_store: dict[str, object] = {"4.running_since": 1561956877}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Four", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert len(results) == 2
    assert isinstance(results[1], Result)
    assert results[1].state == State.WARN
    assert "Running time:" in results[1].summary
    assert "warn/crit at" in results[1].summary


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_idle_normal_runtime(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for idle job with normal runtime."""
    value_store: dict[str, object] = {"6.running_since": 1562056000}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Six", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert len(results) == 2
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "Backup in progress since" in results[0].summary
    assert "currently idle" in results[0].summary

    assert isinstance(results[1], Result)
    assert results[1].state == State.OK
    assert "Running time:" in results[1].summary


@time_machine.travel(1562056877.0)
def test_check_veeam_tapejobs_new_job_no_runtime_tracking(
    parsed_data: veeam_tapejobs.Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check for new working job without existing runtime tracking."""
    value_store: dict[str, object] = {}
    monkeypatch.setattr(veeam_tapejobs, "get_value_store", lambda: value_store)

    results = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Job Four", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert len(results) == 2
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "Backup in progress since" in results[0].summary
    assert isinstance(results[1], Result)
    assert results[1].state == State.OK


def test_check_veeam_tapejobs_nonexistent_item(
    parsed_data: veeam_tapejobs.Section,
) -> None:
    """Test check for non-existent job item."""
    result = list(
        veeam_tapejobs.check_veeam_tapejobs(
            "Nonexistent Job", {"levels_upper": ("fixed", (86400.0, 172800.0))}, parsed_data
        )
    )

    assert result == []
