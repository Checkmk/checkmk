#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Contract tests: the user store reader agrees with the GUI on the files the GUI writes

The product usage package must not import the GUI, so it reads the user store itself. These
tests let the GUI write the files and compare the reader's result with the GUI's own reading.
"""

from collections.abc import Sequence

import pytest

from cmk.ccc.user import UserId
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb import get_last_seen, load_users, save_custom_attr
from cmk.gui.userdb.session import save_session_infos
from cmk.product_usage.collectors.user_store import load_users_with_profiles, StoredUser
from cmk.utils import paths


def test_last_seen_matches_the_gui_for_sessions_and_rest_api_logins(
    with_user: tuple[UserId, str], with_automation_user: tuple[UserId, str]
) -> None:
    session = SessionInfo(
        session_id="sid-1", started_at=1767789000, last_activity=1767790000, auth_type="cookie"
    )
    save_session_infos(with_user[0], {session.session_id: session})
    # What the GUI writes when a request authenticates by a header
    save_custom_attr(
        with_automation_user[0],
        "last_login",
        {"auth_type": "automation", "timestamp": 1767795000, "remote_address": "127.0.0.1"},
    )

    assert sorted(user.last_seen for user in _read_users()) == sorted(
        get_last_seen(user)[0] for user in load_users().values()
    )


@pytest.mark.usefixtures("with_user", "with_automation_user")
def test_automation_flag_matches_the_gui() -> None:
    assert sorted(user.is_automation for user in _read_users()) == sorted(
        bool(user.get("is_automation_user")) for user in load_users().values()
    )


def _read_users() -> Sequence[StoredUser]:
    return load_users_with_profiles(paths.default_config_dir, paths.profile_dir)
