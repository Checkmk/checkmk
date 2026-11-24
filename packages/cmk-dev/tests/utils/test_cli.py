# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest
from cmk_dev_site.utils import cli
from cmk_dev_site.utils.cli import format_duration, report_duration, resolve_argv

PROCESS_ARGV = ["-n", "foo"]


def test_resolve_argv_keeps_an_explicitly_empty_argv() -> None:
    assert resolve_argv([], PROCESS_ARGV) == []


def test_resolve_argv_keeps_given_arguments() -> None:
    assert resolve_argv(["2.3", "--edition", "cee"], PROCESS_ARGV) == ["2.3", "--edition", "cee"]


def test_resolve_argv_falls_back_only_for_none() -> None:
    assert resolve_argv(None, PROCESS_ARGV) == PROCESS_ARGV


@pytest.mark.parametrize(
    "seconds, expected",
    [
        pytest.param(4.24, "4.2s", id="below-a-minute-shows-one-decimal"),
        pytest.param(59.96, "1m 00s", id="rounding-up-to-a-minute-avoids-60.0s"),
        pytest.param(125, "2m 05s", id="minutes-and-seconds"),
        pytest.param(3725, "1h 02m 05s", id="hours-minutes-and-seconds"),
    ],
)
def test_format_duration_switches_to_minutes_and_hours(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Make the next `report_duration` run appear to take the given number of seconds."""

    def set_elapsed(seconds: float) -> None:
        ticks = iter([100.0, 100.0 + seconds])
        monkeypatch.setattr(cli.time, "monotonic", lambda: next(ticks))  # type: ignore[attr-defined]

    return set_elapsed


def test_report_duration_prints_to_stderr(
    capsys: pytest.CaptureFixture[str], fake_clock: Callable[[float], None]
) -> None:
    fake_clock(125)
    with report_duration():
        pass

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "\nTook 2m 05s\n"


def test_report_duration_skips_very_short_runs(
    capsys: pytest.CaptureFixture[str], fake_clock: Callable[[float], None]
) -> None:
    fake_clock(0.2)
    with report_duration():
        pass

    assert capsys.readouterr().err == ""


def test_report_duration_reports_only_once_when_nested(
    capsys: pytest.CaptureFixture[str], fake_clock: Callable[[float], None]
) -> None:
    fake_clock(5)
    with report_duration(), report_duration():
        pass

    assert capsys.readouterr().err.count("Took ") == 1


def test_report_duration_reports_on_failure(
    capsys: pytest.CaptureFixture[str], fake_clock: Callable[[float], None]
) -> None:
    fake_clock(5)
    with pytest.raises(RuntimeError), report_duration():
        raise RuntimeError("command failed")

    assert "Took " in capsys.readouterr().err
