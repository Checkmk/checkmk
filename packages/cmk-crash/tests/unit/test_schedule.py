#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from pathlib import Path

import pytest

from cmk.crash_reporting._schedule import claim_due_run

_NOW = datetime(2026, 7, 28, 12, 0, 0).timestamp()
_HOUR = 3600
_STATE_FILE = "var/check_mk/crash_upload_next_run"


def test_first_call_arms_a_slot_in_the_spread_window_and_does_not_run(tmp_path: Path) -> None:
    """A fleet enabled in one push must not flush every backlog in the same tick."""
    assert claim_due_run(tmp_path, _NOW) is False

    assert _NOW <= int((tmp_path / _STATE_FILE).read_text()) <= _NOW + 2 * _HOUR


@pytest.mark.parametrize(
    "observed_late_by",
    [
        pytest.param(_HOUR, id="tick-an-hour-after-the-due-point"),
        pytest.param(1.4, id="startup-latency-over-a-whole-second"),
    ],
)
def test_run_schedules_one_interval_from_the_due_point_not_from_the_tick(
    tmp_path: Path, observed_late_by: float
) -> None:
    """A cron tick observes the due point up to 30 min late. Anchoring the next point on
    the tick instead would push the slot later and walk it around the clock."""
    claim_due_run(tmp_path, _NOW)
    armed = int((tmp_path / _STATE_FILE).read_text())

    assert claim_due_run(tmp_path, armed + observed_late_by) is True
    assert int((tmp_path / _STATE_FILE).read_text()) == armed + 24 * _HOUR


def test_call_before_the_scheduled_point_is_not_due(tmp_path: Path) -> None:
    claim_due_run(tmp_path, _NOW)
    armed = int((tmp_path / _STATE_FILE).read_text())
    claim_due_run(tmp_path, armed)  # runs, and schedules a day on
    scheduled = (tmp_path / _STATE_FILE).read_text()

    assert claim_due_run(tmp_path, armed + _HOUR) is False
    assert (tmp_path / _STATE_FILE).read_text() == scheduled


def test_run_after_long_downtime_resumes_from_now(tmp_path: Path) -> None:
    """Anchoring strictly on the due point would fire once per tick until every slot
    missed while the site was down had been used up."""
    claim_due_run(tmp_path, _NOW)
    armed = int((tmp_path / _STATE_FILE).read_text())
    back_up_again = armed + 7 * 24 * _HOUR

    assert claim_due_run(tmp_path, back_up_again) is True
    assert int((tmp_path / _STATE_FILE).read_text()) == back_up_again + 24 * _HOUR


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("", id="empty"),
        pytest.param("not-a-timestamp", id="garbage"),
        pytest.param("99999999999", id="implausibly-far-future"),
    ],
)
def test_unusable_state_file_is_rearmed(tmp_path: Path, content: str) -> None:
    """The file is hand-editable and a clock jump ahead can push it years out. Neither may
    wedge uploads until the point it names, and nothing else ever rearms."""
    state_file = tmp_path / _STATE_FILE
    state_file.parent.mkdir(parents=True)
    state_file.write_text(content)

    assert claim_due_run(tmp_path, _NOW) is False
    assert _NOW <= int(state_file.read_text()) <= _NOW + 2 * _HOUR
