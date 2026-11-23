#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.product_usage.collectors.sessions as sessions_collector
from cmk.product_usage.schema import SessionStats

NOW = 1767790000
WEEK = 7 * 24 * 3600


def test_session_statistics_describe_the_durations_from_start_to_last_activity(
    tmp_path: Path,
) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [
            _StoredSession(session_id=f"sid-{i}", started_at=NOW - 3600, duration=duration)
            for i, duration in enumerate([2, 4, 4, 4, 5, 5, 7, 9])
        ],
    )

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats == SessionStats(
        count=8, average_duration=5.0, median_duration=4.5, stddev_duration=2.0
    )


def test_single_session_has_a_standard_deviation_of_zero(tmp_path: Path) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [_StoredSession(session_id="sid-1", started_at=NOW - 3600, duration=1000)],
    )

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats == SessionStats(
        count=1, average_duration=1000.0, median_duration=1000.0, stddev_duration=0.0
    )


def test_sessions_of_all_users_are_counted(tmp_path: Path) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [_StoredSession(session_id="sid-1", started_at=NOW - 3600, duration=1000)],
    )
    _write_sessions(
        tmp_path,
        "bob@acme.com",
        [_StoredSession(session_id="sid-2", started_at=NOW - 3600, duration=1000)],
    )

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats.count == 2


def test_only_sessions_that_started_in_the_seven_days_before_the_collection_are_counted(
    tmp_path: Path,
) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [
            # Active in the window, but counted by the run before
            _StoredSession(session_id="sid-1", started_at=NOW - WEEK, duration=3600),
            _StoredSession(session_id="sid-2", started_at=NOW - WEEK + 1, duration=1000),
        ],
    )

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats == SessionStats(
        count=1, average_duration=1000.0, median_duration=1000.0, stddev_duration=0.0
    )


def test_no_session_in_the_window_has_a_count_of_zero_and_no_duration_statistics(
    tmp_path: Path,
) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [_StoredSession(session_id="sid-1", started_at=NOW - 2 * WEEK, duration=1000)],
    )

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats == SessionStats(
        count=0, average_duration=None, median_duration=None, stddev_duration=None
    )


def test_user_that_never_logged_in_has_no_sessions(tmp_path: Path) -> None:
    (tmp_path / "web/api_user").mkdir(parents=True)

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats.count == 0


def test_user_whose_first_session_is_being_saved_has_no_sessions(tmp_path: Path) -> None:
    # The GUI's lock creates the file empty before the first session is written to it
    path = tmp_path / "web/jane@acme.com/session_info.mk"
    path.parent.mkdir(parents=True)
    path.touch()

    stats = sessions_collector.collect(tmp_path, now=NOW)

    assert stats.count == 0


@dataclass(frozen=True, kw_only=True)
class _StoredSession:
    session_id: str
    started_at: int
    duration: int


def _write_sessions(var_dir: Path, user_id: str, sessions: Sequence[_StoredSession]) -> None:
    """Write the sessions of the user in the format of the GUI's session store"""
    path = var_dir / "web" / user_id / "session_info.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        repr(
            {
                session.session_id: {
                    "session_id": session.session_id,
                    "started_at": session.started_at,
                    "last_activity": session.started_at + session.duration,
                    "csrf_token": "0f8fad5b-d9cb-469f-a165-70867728950e",
                    "flashes": [],
                    "encrypter_secret": "c2VjcmV0",
                    "two_factor_required": False,
                    "webauthn_action_state": None,
                    "auth_type": "cookie",
                    "session_state": "logged_in",
                }
                for session in sessions
            }
        )
        + "\n"
    )
