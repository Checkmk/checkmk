#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from cmk.ccc.user import UserId
from cmk.gui.userdb.session import load_session_infos
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.migrate_session_info import MigrateSessionInfo
from cmk.utils.paths import profile_dir


def run_migrate_session_info() -> None:
    MigrateSessionInfo(
        name="migrate_session_info",
        title="Migrating all existing user sessions",
        sort_index=25,
        expiry_version=ExpiryVersion.CMK_260,
    )(logging.getLogger())


def test_valid_info_is_migrated(with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    session_data = {
        "111111-1111-1111-1111-111111111111": {
            "session_id": "111111-1111-1111-1111-111111111111",
            "started_at": 1765295913,
            "last_activity": 1765298116,
            "csrf_token": "5493895d-a2eb-40b0-a51b-3d005ed733f8",
            "flashes": [],
            "encrypter_secret": "iRE6in6DGIeAmzkP9vN8DIz3guWA5RGjOMbaGKxCt0A=",
            "two_factor_completed": False,
            "two_factor_required": False,
            "webauthn_action_state": None,
            "logged_out": False,
            "auth_type": "cookie",
        },
        "222222-2222-2222-2222-222222222222": {
            "session_id": "222222-2222-2222-2222-222222222222",
            "started_at": 1765295913,
            "last_activity": 1765298116,
            "csrf_token": "5493895d-a2eb-40b0-a51b-3d005ed733f8",
            "flashes": [],
            "encrypter_secret": "iRE6in6DGIeAmzkP9vN8DIz3guWA5RGjOMbaGKxCt0A=",
            "two_factor_completed": False,
            "two_factor_required": False,
            "webauthn_action_state": None,
            "logged_out": False,
            "auth_type": "cookie",
        },
    }
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text(
        repr(session_data)
    )

    run_migrate_session_info()

    assert session_info_file.exists()
    session_info = load_session_infos(username)
    assert "111111-1111-1111-1111-111111111111" in session_info
    assert session_info["111111-1111-1111-1111-111111111111"].encrypter_secret == (
        "iRE6in6DGIeAmzkP9vN8DIz3guWA5RGjOMbaGKxCt0A="
    )
    assert "222222-2222-2222-2222-222222222222" in session_info
    assert session_info["222222-2222-2222-2222-222222222222"].session_state == "credentials_needed"


def test_pre_20_info_is_migrated(with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    timestamp = 1234567890
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text(
        f"sess2|{timestamp}"
    )

    run_migrate_session_info()

    assert session_info_file.exists()
    session_info = load_session_infos(username)
    assert "sess2" in session_info
    assert session_info["sess2"].started_at == timestamp
    assert session_info["sess2"].last_activity == timestamp


def test_empty_info_preserved(with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text("")

    run_migrate_session_info()

    assert session_info_file.read_text() == ""
    load_session_infos(username)


def test_incomplete_info_deleted(with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text(
        repr(
            {
                "333333-3333-3333-3333-333333333333": {
                    "session_id": "333333-3333-3333-3333-333333333333",
                },
            },
        )
    )

    run_migrate_session_info()

    assert not session_info_file.exists()
    load_session_infos(username)


def test_broken_info_deleted(with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text(
        "this is not a valid repr!"
    )

    run_migrate_session_info()

    assert not session_info_file.exists()
    load_session_infos(username)


def test_idempotency(with_user: tuple[UserId, str]) -> None:
    session_data = """{
        "9787d6e0-b1db-454d-aaf0-f7ab0e47e6ed": {
            "session_id": "9787d6e0-b1db-454d-aaf0-f7ab0e47e6ed",
            "started_at": 1765882365,
            "last_activity": 1765882376,
            "csrf_token": "26473306-9ffe-4dbe-a4ae-6f9d0c6630f7",
            "flashes": [],
            "encrypter_secret": "+HurkwwLdn73GuBfN/zCiAEe1tnOMCj/VZD8NzQMM0k=",
            "two_factor_required": False,
            "webauthn_action_state": None,
            "auth_type": "cookie",
            "session_state": "logged_in",
        }
    }"""
    username, _ = with_user
    (session_info_file := Path(profile_dir / username / "session_info.mk")).write_text(session_data)

    run_migrate_session_info()

    assert session_info_file.read_text() == session_data
    load_session_infos(username)
