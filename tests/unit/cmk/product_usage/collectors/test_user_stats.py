#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import cmk.product_usage.collectors.user_stats as user_stats_collector
from cmk.product_usage.collectors.user_store import load_users_with_profiles
from cmk.product_usage.schema import UsersData

NOW = 1767700800
DAY = 86400


@pytest.fixture(name="config_dir")
def fixture_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "etc"
    (config_dir / "multisite.d" / "wato").mkdir(parents=True)
    return config_dir


@pytest.fixture(name="profile_dir")
def fixture_profile_dir(tmp_path: Path) -> Path:
    profile_dir = tmp_path / "web"
    profile_dir.mkdir()
    return profile_dir


def _collect(config_dir: Path, profile_dir: Path) -> UsersData:
    return user_stats_collector.collect(
        load_users_with_profiles(config_dir, profile_dir), config_dir, NOW
    )


def _write_users(config_dir: Path, users: Mapping[str, Mapping[str, object]]) -> None:
    (config_dir / "multisite.d" / "wato" / "users.mk").write_text(f"multisite_users = {users!r}\n")


def _write_connections(config_dir: Path, connections: Sequence[Mapping[str, object]]) -> None:
    (config_dir / "multisite.d" / "wato" / "user_connections.mk").write_text(
        f"user_connections = {list(connections)!r}\n"
    )


def _write_profile_file(profile_dir: Path, user_id: str, name: str, value: object) -> None:
    (profile_dir / user_id).mkdir(exist_ok=True)
    (profile_dir / user_id / name).write_text(f"{value!r}\n")


def test_collect_without_users_file(config_dir: Path, profile_dir: Path) -> None:
    data = _collect(config_dir, profile_dir)

    assert data["humans"] == {
        "total": 0,
        "by_role": {},
        "by_connector_type": {},
        "active": {"24h": 0, "7d": 0, "30d": 0},
    }


def test_collect_separates_automation_users(config_dir: Path, profile_dir: Path) -> None:
    _write_users(
        config_dir,
        {
            "cmkadmin": {"roles": ["admin"]},
            "automation": {"roles": ["admin"]},
            "agent_registration": {"roles": ["agent_registration"]},
        },
    )
    _write_profile_file(profile_dir, "automation", "automation_user.mk", True)
    # Users created before 2.4 only have the secret
    _write_profile_file(profile_dir, "agent_registration", "automation.secret", "secret")

    data = _collect(config_dir, profile_dir)

    assert (data["humans"]["total"], data["humans"]["by_role"]) == (1, {"admin": 1})
    assert (data["automation"]["total"], data["automation"]["by_role"]) == (
        2,
        {"admin": 1, "agent_registration": 1},
    )


def test_collect_counts_custom_roles_as_custom(config_dir: Path, profile_dir: Path) -> None:
    _write_users(
        config_dir,
        {
            "alice": {"roles": ["user", "noc_operators", "dba"]},
            "bob": {"roles": ["guest"]},
        },
    )

    data = _collect(config_dir, profile_dir)

    assert data["humans"]["by_role"] == {"user": 1, "custom": 1, "guest": 1}


def test_collect_reports_connector_type_not_id(config_dir: Path, profile_dir: Path) -> None:
    _write_users(
        config_dir,
        {
            "local": {"roles": ["user"]},
            "ad_user": {"roles": ["user"], "connector": "corp_example_com"},
            "orphan": {"roles": ["user"], "connector": "deleted_connection"},
        },
    )
    _write_connections(config_dir, [{"id": "corp_example_com", "type": "ldap"}])

    data = _collect(config_dir, profile_dir)

    assert data["humans"]["by_connector_type"] == {"htpasswd": 1, "ldap": 1, "unknown": 1}


def test_collect_counts_activity_from_sessions_and_logins(
    config_dir: Path, profile_dir: Path
) -> None:
    _write_users(
        config_dir,
        {
            "gui_today": {"roles": ["user"]},
            "api_last_week": {"roles": ["user"]},
            "gui_last_month": {"roles": ["user"]},
            "long_ago": {"roles": ["user"]},
            "never": {"roles": ["user"]},
        },
    )
    _write_profile_file(
        profile_dir,
        "gui_today",
        "session_info.mk",
        {
            "old": {"session_id": "old", "started_at": 0, "last_activity": NOW - 20 * DAY},
            "new": {"session_id": "new", "started_at": 0, "last_activity": NOW - 3600},
        },
    )
    _write_profile_file(
        profile_dir,
        "api_last_week",
        "last_login.mk",
        {"auth_type": "bearer", "timestamp": NOW - 3 * DAY, "remote_address": "127.0.0.1"},
    )
    _write_profile_file(
        profile_dir,
        "gui_last_month",
        "session_info.mk",
        {"s": {"session_id": "s", "started_at": 0, "last_activity": NOW - 20 * DAY}},
    )
    _write_profile_file(
        profile_dir,
        "long_ago",
        "last_login.mk",
        {"auth_type": "bearer", "timestamp": NOW - 40 * DAY, "remote_address": "127.0.0.1"},
    )

    data = _collect(config_dir, profile_dir)

    assert data["humans"]["active"] == {"24h": 1, "7d": 2, "30d": 3}


@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("last_login.mk", id="last login"),
        pytest.param("session_info.mk", id="sessions"),
    ],
)
def test_collect_counts_user_with_unreadable_activity_as_inactive(
    config_dir: Path, profile_dir: Path, filename: str
) -> None:
    _write_users(config_dir, {"jane": {"roles": ["user"]}})
    (profile_dir / "jane").mkdir()
    (profile_dir / "jane" / filename).write_text("{")

    data = _collect(config_dir, profile_dir)

    assert (data["humans"]["total"], data["humans"]["active"]) == (
        1,
        {"24h": 0, "7d": 0, "30d": 0},
    )
