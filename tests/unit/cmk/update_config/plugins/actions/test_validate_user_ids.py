#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Any

import pytest

from cmk.gui.userdb import load_multisite_users
from cmk.gui.userdb.store import _multisite_dir, save_to_mk_file

from cmk.update_config.plugins.actions.validate_user_ids import ValidateUserIds


@pytest.fixture(name="run_check")
def fixture_check_pw_hashes_action() -> ValidateUserIds:
    """Action to test as it's registered in the real world"""

    return ValidateUserIds(
        name="validate_user_ids",
        title="Validate user IDs",
        sort_index=5,
        continue_on_failure=False,
    )


@pytest.fixture(name="with_invalid_user")
def fixture_with_invalid_user(with_user: Any) -> Iterator[None]:
    orig_users = load_multisite_users()
    invalid_user = {"invalid user": {"connector": "htpasswd"}}

    save_to_mk_file(
        "{}/{}".format(_multisite_dir(), "users.mk"),
        "multisite_users",
        orig_users | invalid_user,
    )
    yield

    save_to_mk_file(
        "{}/{}".format(_multisite_dir(), "users.mk"),
        "multisite_users",
        orig_users,
    )


class _MockLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def error(self, msg: str) -> None:
        self.messages.append(msg)


def test_no_invalid_user_in_mk_files(with_user: None, run_check: ValidateUserIds) -> None:
    """Invalid users in users.mk and in contacts.mk are detected"""
    mock_logger = _MockLogger()
    run_check(mock_logger, {})  # type: ignore[arg-type]

    assert len(mock_logger.messages) == 0


def test_invalid_user_in_mk_files(with_invalid_user: None, run_check: ValidateUserIds) -> None:
    """Invalid users in users.mk and in contacts.mk are detected"""
    mock_logger = _MockLogger()
    with pytest.raises(ValueError, match="invalid user"):
        run_check(mock_logger, {})  # type: ignore[arg-type]

    assert len(mock_logger.messages) == 1
    assert "Incompatible user IDs have been found" in mock_logger.messages[0]
