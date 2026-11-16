#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.product_usage.collectors.sessions as sessions_collector
from cmk.product_usage.schema import Session


def test_session_has_its_start_and_last_activity_time_unchanged(tmp_path: Path) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [_StoredSession(session_id="sid-1", started_at=1767789000, last_activity=1767790000)],
    )

    sessions = sessions_collector.collect(tmp_path)

    assert sessions == [Session(started_at=1767789000, last_activity=1767790000)]


def test_sessions_include_every_stored_session_of_a_user(tmp_path: Path) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [
            _StoredSession(session_id="sid-1", started_at=1767789000, last_activity=1767790000),
            _StoredSession(session_id="sid-2", started_at=1767800000, last_activity=1767801000),
        ],
    )

    sessions = sessions_collector.collect(tmp_path)

    assert sessions == [
        Session(started_at=1767789000, last_activity=1767790000),
        Session(started_at=1767800000, last_activity=1767801000),
    ]


def test_sessions_of_different_users_are_ordered_by_start_time_not_by_user(
    tmp_path: Path,
) -> None:
    _write_sessions(
        tmp_path,
        "jane@acme.com",
        [
            _StoredSession(session_id="sid-1", started_at=1767789000, last_activity=1767815000),
            _StoredSession(session_id="sid-3", started_at=1767810000, last_activity=1767811000),
        ],
    )
    _write_sessions(
        tmp_path,
        "bob@acme.com",
        [_StoredSession(session_id="sid-2", started_at=1767800000, last_activity=1767801000)],
    )

    sessions = sessions_collector.collect(tmp_path)

    assert sessions == [
        Session(started_at=1767789000, last_activity=1767815000),
        Session(started_at=1767800000, last_activity=1767801000),
        Session(started_at=1767810000, last_activity=1767811000),
    ]


def test_user_that_never_logged_in_has_no_sessions(tmp_path: Path) -> None:
    (tmp_path / "web/api_user").mkdir(parents=True)

    sessions = sessions_collector.collect(tmp_path)

    assert sessions == []


def test_user_whose_first_session_is_being_saved_has_no_sessions(tmp_path: Path) -> None:
    # The GUI's lock creates the file empty before the first session is written to it
    path = tmp_path / "web/jane@acme.com/session_info.mk"
    path.parent.mkdir(parents=True)
    path.touch()

    sessions = sessions_collector.collect(tmp_path)

    assert sessions == []


@dataclass(frozen=True, kw_only=True)
class _StoredSession:
    session_id: str
    started_at: int
    last_activity: int


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
                    "last_activity": session.last_activity,
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
