#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from datetime import datetime

import pytest

from cmk.ccc.user import UserId
from cmk.gui import hooks
from cmk.gui.type_defs import QuarantineInfo, Users, UserSpec
from cmk.gui.userdb import get_user_attributes
from cmk.gui.userdb._ldap_quarantine_cleanup import (
    _expired_quarantined_users,
    expire_quarantined_users,
)
from cmk.gui.userdb.store import load_users, save_users

_DAY = 86400


def _quarantined_user(quarantined_on: int) -> UserSpec:
    return UserSpec(
        connector="ldap1",
        locked=True,
        ldap_quarantine=QuarantineInfo(quarantined_on=quarantined_on, connection_id="ldap1"),
    )


@pytest.fixture(name="announced_deletions")
def fixture_announced_deletions() -> Iterator[list[Sequence[UserId]]]:
    announced: list[Sequence[UserId]] = []
    hooks.register_builtin("users-deleted", announced.append)
    yield announced
    hooks.unregister("users-deleted", announced.append)


def test_expired_quarantined_users_deletes_after_retention() -> None:
    now = 100 * _DAY
    users = Users({UserId("bob"): _quarantined_user(now - 31 * _DAY)})
    assert _expired_quarantined_users(users, now, 30 * _DAY) == [UserId("bob")]


def test_expired_quarantined_users_keeps_within_retention() -> None:
    now = 100 * _DAY
    users = Users({UserId("bob"): _quarantined_user(now - 29 * _DAY)})
    assert _expired_quarantined_users(users, now, 30 * _DAY) == []


def test_expired_quarantined_users_boundary_is_strictly_greater() -> None:
    now = 100 * _DAY
    users = Users({UserId("bob"): _quarantined_user(now - 30 * _DAY)})
    # exactly at the retention period must not yet expire
    assert _expired_quarantined_users(users, now, 30 * _DAY) == []


def test_expired_quarantined_users_ignores_non_quarantined() -> None:
    now = 100 * _DAY
    users = Users(
        {
            UserId("alice"): UserSpec(connector="ldap1", locked=False),
            UserId("bob"): _quarantined_user(now - 31 * _DAY),
        }
    )
    assert _expired_quarantined_users(users, now, 30 * _DAY) == [UserId("bob")]


@pytest.mark.usefixtures("request_context")
def test_expiring_quarantined_users_announces_their_deletion(
    announced_deletions: list[Sequence[UserId]],
) -> None:
    now = datetime.fromtimestamp(100 * _DAY)
    save_users(
        profiles={**load_users(lock=True), UserId("bob"): _quarantined_user(69 * _DAY)},
        user_attributes=get_user_attributes([]),
        user_connections=[],
        now=now,
        pprint_value=False,
        call_users_saved_hook=False,
    )

    expire_quarantined_users(now, 30 * _DAY)

    assert announced_deletions == [[UserId("bob")]]
