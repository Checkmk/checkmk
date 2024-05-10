#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from typing import Any

import pytest

from cmk.utils.store import save_to_mk_file

from cmk.gui.userdb import load_multisite_users
from cmk.gui.userdb.store import _multisite_dir

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


def test_no_invalid_user_in_mk_files(
    with_user: None, run_check: ValidateUserIds, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid users in users.mk and in contacts.mk are detected"""
    caplog.set_level(logging.INFO)
    run_check(logging.getLogger())

    assert len(caplog.messages) == 0


def test_invalid_user_in_mk_files(
    with_invalid_user: None,
    run_check: ValidateUserIds,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Invalid users in users.mk and in contacts.mk are detected"""
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError, match="invalid user"):
        run_check(logging.getLogger())
    assert len(caplog.messages) == 1
    assert "Incompatible user IDs have been found" in caplog.messages[0]
