#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta

import pytest

from cmk.ccc.user import UserId
from cmk.gui.userdb._login_timeout import (
    ENTRY_STORAGE_LIFETIME,
    IP_TIMEOUT_DURATION,
    LoginTimeoutStore,
    USER_ATTEMPT_LIMIT,
    USER_TIMEOUT_DURATION,
)

NOW = datetime(2026, 1, 1, 12, 0, 0)
LATER = datetime(2026, 1, 1, 12, 0, 30)
LATEST = datetime(2026, 1, 1, 12, 1, 0)

REMOTE_IP = "192.168.1.105"


def _read_timeout_data() -> dict[str, dict[str, dict[str, object]]]:
    return LoginTimeoutStore()._read().model_dump(mode="json")


def _time_out_user_from_ip(user_id: UserId, remote_ip: str, now: datetime) -> None:
    for _ in range(USER_ATTEMPT_LIMIT):
        LoginTimeoutStore().record_failed_login(user_id, remote_ip, now)


@pytest.mark.parametrize(
    ["attempts", "expected_users", "expected_ip_count", "expected_ip_usernames"],
    [
        (
            [(UserId("alice"), "192.168.1.105", NOW)],
            {
                "alice": {
                    "attempts": 1,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": None,
                }
            },
            0,
            None,
        ),
        (
            [
                (UserId("alice"), "192.168.1.105", NOW),
                (UserId("alice"), "192.168.1.105", LATER),
                (UserId("alice"), "192.168.1.105", LATEST),
            ],
            {
                "alice": {
                    "attempts": 3,
                    "last_attempt": LATEST.isoformat(),
                    "timed_out_at": None,
                }
            },
            0,
            None,
        ),
        (
            [
                (UserId("alice"), "192.168.1.105", NOW),
                (UserId("admin"), "10.0.0.47", NOW),
            ],
            {
                "alice": {
                    "attempts": 1,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": None,
                },
                "admin": {
                    "attempts": 1,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": None,
                },
            },
            0,
            None,
        ),
        (
            [(UserId("alice"), None, NOW)],
            {
                "alice": {
                    "attempts": 1,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": None,
                }
            },
            0,
            None,
        ),
        (
            [(UserId("alice"), "192.168.1.105", NOW)] * USER_ATTEMPT_LIMIT,
            {
                "alice": {
                    "attempts": USER_ATTEMPT_LIMIT,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": NOW.isoformat(),
                }
            },
            1,
            ["alice"],
        ),
        (
            [(UserId("alice"), "192.168.1.105", NOW)] * (USER_ATTEMPT_LIMIT + 3),
            {
                "alice": {
                    "attempts": USER_ATTEMPT_LIMIT + 3,
                    "last_attempt": NOW.isoformat(),
                    "timed_out_at": NOW.isoformat(),
                }
            },
            1,
            ["alice"],
        ),
    ],
    ids=[
        "single_failed_attempt",
        "multiple_attempts_for_same_user",
        "tracks_multiple_users",
        "without_remote_ip_only_tracks_user",
        "adds_single_ip_entry_once_user_limit_reached",
        "ip_entry_not_repeated_past_user_limit",
    ],
)
def test_login_timeout_handles_failed_login(
    attempts: list[tuple[UserId, str | None, datetime]],
    expected_users: dict[str, dict[str, int | str | None]],
    expected_ip_count: int,
    expected_ip_usernames: list[str] | None,
) -> None:
    """Test base outcomes of a failed login"""
    for user_id, remote_ip, now in attempts:
        LoginTimeoutStore().record_failed_login(user_id, remote_ip, now)

    registry = _read_timeout_data()
    assert registry["users"] == expected_users
    assert len(registry["ips"]) == expected_ip_count
    if expected_ip_count:
        assert all(entry["attempts"] == expected_ip_usernames for entry in registry["ips"].values())


@pytest.mark.parametrize(
    "user_id_to_clear",
    [UserId("alice"), UserId("someone_else")],
    ids=["single_user_exist", "multiple_users_exist"],
)
def test_login_timeout_removes_user_entry_on_successful_login(user_id_to_clear: UserId) -> None:
    """Test that only the correct user entry is removed when directly cleared"""
    _time_out_user_from_ip(UserId("alice"), REMOTE_IP, NOW)
    LoginTimeoutStore().record_failed_login(UserId("admin"), "10.0.0.47", NOW)

    LoginTimeoutStore().clear_on_success(user_id_to_clear, NOW)

    registry = _read_timeout_data()
    assert ("alice" in registry["users"]) == (user_id_to_clear != "alice")
    assert registry["users"]["admin"] == {
        "attempts": 1,
        "last_attempt": NOW.isoformat(),
        "timed_out_at": None,
    }
    assert len(registry["ips"]) == 1


def test_login_timeout_user_duration_checks() -> None:
    """Ensure timeouts have a ttl"""
    now = NOW
    user = UserId("alice")
    _time_out_user_from_ip(user, REMOTE_IP, now)
    assert LoginTimeoutStore().is_timed_out(user, REMOTE_IP, now)

    now += USER_TIMEOUT_DURATION - timedelta(seconds=1)
    assert LoginTimeoutStore().is_timed_out(user, REMOTE_IP, now)

    now += timedelta(seconds=1)
    assert not LoginTimeoutStore().is_timed_out(user, REMOTE_IP, now)

    now += timedelta(seconds=1)
    assert not LoginTimeoutStore().is_timed_out(user, REMOTE_IP, now)


def test_login_timeout_ip_timeout_works() -> None:
    now = NOW
    new_user = UserId("newuser")
    _time_out_user_from_ip(UserId("alice"), REMOTE_IP, now)
    _time_out_user_from_ip(UserId("bob"), REMOTE_IP, now)

    # A user is blocked by IP
    assert LoginTimeoutStore().is_timed_out(new_user, REMOTE_IP, now)

    now += IP_TIMEOUT_DURATION - timedelta(seconds=1)
    assert LoginTimeoutStore().is_timed_out(new_user, REMOTE_IP, now)

    now += timedelta(seconds=1)
    assert not LoginTimeoutStore().is_timed_out(new_user, REMOTE_IP, now)

    now += timedelta(seconds=1)
    assert not LoginTimeoutStore().is_timed_out(new_user, REMOTE_IP, now)


@pytest.mark.parametrize(
    ["attempts_for_alice", "check_user_id"],
    [
        (USER_ATTEMPT_LIMIT - 1, UserId("alice")),
        (USER_ATTEMPT_LIMIT, UserId("newuser")),
    ],
    ids=["user_limit", "ip_limit"],
)
def test_login_timeout_limits_enforced(attempts_for_alice: int, check_user_id: UserId) -> None:
    for _ in range(attempts_for_alice):
        LoginTimeoutStore().record_failed_login(UserId("alice"), REMOTE_IP, NOW)

    assert LoginTimeoutStore().is_timed_out(check_user_id, REMOTE_IP, NOW) is False


def test_login_timeout_ip_timeout_require_unique_users() -> None:
    _time_out_user_from_ip(UserId("alice"), REMOTE_IP, NOW)

    after_expiry = NOW + USER_TIMEOUT_DURATION + timedelta(seconds=1)
    _time_out_user_from_ip(UserId("alice"), REMOTE_IP, after_expiry)

    (ip_entry,) = _read_timeout_data()["ips"].values()
    assert ip_entry["attempts"] == ["alice"]
    assert LoginTimeoutStore().is_timed_out(UserId("newuser"), REMOTE_IP, after_expiry) is False


@pytest.mark.parametrize(
    ["initial_timeouts", "retry_username", "check_user_id", "duration"],
    [
        ([UserId("alice")], UserId("alice"), UserId("alice"), USER_TIMEOUT_DURATION),
        (
            [UserId("alice"), UserId("bob")],
            UserId("jeff"),
            UserId("newuser"),
            IP_TIMEOUT_DURATION,
        ),
    ],
    ids=["user", "ip"],
)
def test_login_timeout_durations_not_reset_within_existing_timeout(
    initial_timeouts: list[UserId],
    retry_username: UserId,
    check_user_id: UserId,
    duration: timedelta,
) -> None:
    for username in initial_timeouts:
        _time_out_user_from_ip(username, REMOTE_IP, NOW)
    _time_out_user_from_ip(retry_username, REMOTE_IP, NOW + duration / 2)

    after_expiry = NOW + duration + timedelta(seconds=1)
    assert LoginTimeoutStore().is_timed_out(check_user_id, REMOTE_IP, after_expiry) is False


def test_login_timeout_purges_old_data() -> None:
    LoginTimeoutStore().record_failed_login(UserId("alice"), REMOTE_IP, NOW)
    LoginTimeoutStore().record_failed_login(UserId("admin"), "10.0.0.47", NOW)

    later = NOW + ENTRY_STORAGE_LIFETIME + timedelta(seconds=1)
    assert LoginTimeoutStore().is_timed_out(UserId("alice"), REMOTE_IP, later) is False

    registry = _read_timeout_data()
    assert registry["users"] == {}
    assert registry["ips"] == {}


def test_login_timeout_purges_old_data_unless_linked_to_active_timeout() -> None:
    _time_out_user_from_ip(UserId("alice"), REMOTE_IP, NOW)
    _time_out_user_from_ip(UserId("bob"), REMOTE_IP, NOW)
    within_ip_duration = NOW + ENTRY_STORAGE_LIFETIME + timedelta(minutes=5)
    assert (
        LoginTimeoutStore().is_timed_out(UserId("newuser"), REMOTE_IP, within_ip_duration) is True
    )
    assert _read_timeout_data()["ips"]

    after_ip_duration = NOW + IP_TIMEOUT_DURATION + timedelta(seconds=1)
    assert (
        LoginTimeoutStore().is_timed_out(UserId("newuser"), REMOTE_IP, after_ip_duration) is False
    )

    registry = _read_timeout_data()
    assert registry["users"] == {}
    assert registry["ips"] == {}
