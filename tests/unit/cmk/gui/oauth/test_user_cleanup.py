#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import pytest

from cmk.ccc.user import UserId
from cmk.gui import hooks
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.token.backend import OAUTH_DATABASE_BACKEND, OAUTH_DATABASE_NAME
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.scopes import DEFAULT_SCOPE
from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.userdb import get_user_attributes
from cmk.gui.userdb.store import load_users, save_users
from cmk.gui.userdb.userdata import UserDB

_KEPT = UserId("kept")
_DELETED = UserId("deleted")


def _write_users(users: Users) -> None:
    save_users(
        profiles=users,
        user_attributes=get_user_attributes([]),
        user_connections=[],
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
    )


def _seed_users() -> None:
    _write_users(
        {
            **load_users(lock=True),
            _KEPT: UserSpec({"alias": "Kept", "roles": []}),
            _DELETED: UserSpec({"alias": "Deleted", "roles": []}),
        }
    )


def _start_grant(user_id: UserId) -> str:
    """The refresh token of a new grant of the user."""
    with get_client_store() as clients:
        registration = clients.register(["https://client.example/callback"], None)
    assert registration.is_ok()
    now = datetime.now(UTC)
    with get_token_store() as tokens:
        issued = tokens.start_grant(
            user_id,
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=registration.ok.client_id,
            expires_at=now + timedelta(days=1),
            refresh_token_expires_at=now + timedelta(hours=1),
            access_token_expires_at=now + timedelta(minutes=5),
        )
    assert issued.is_ok()
    return issued.ok.refresh


def _is_usable(refresh_token: str) -> bool:
    with get_token_store() as tokens:
        return tokens.get_refresh_token(refresh_token) is not None


def _delete_user(user_id: UserId) -> None:
    UserDB(get_user_attributes([]), [], pprint_value=False).delete_users([user_id])


@pytest.mark.usefixtures("request_context")
def test_deleting_a_user_revokes_their_oauth_grants() -> None:
    _seed_users()
    refresh_token = _start_grant(_DELETED)

    _delete_user(_DELETED)

    assert not _is_usable(refresh_token)


@pytest.mark.usefixtures("request_context")
def test_deleting_a_user_keeps_the_oauth_grants_of_the_other_users() -> None:
    _seed_users()
    refresh_token = _start_grant(_KEPT)

    _delete_user(_DELETED)

    assert _is_usable(refresh_token)


@pytest.mark.usefixtures("request_context")
def test_a_config_sync_that_removes_a_user_revokes_their_oauth_grants() -> None:
    _seed_users()
    refresh_token = _start_grant(_DELETED)
    # The sync replaces the users file of a remote site, deleting no user
    # on its own.
    _write_users({user_id: spec for user_id, spec in load_users().items() if user_id != _DELETED})

    hooks.call("snapshot-pushed")

    assert not _is_usable(refresh_token)


@pytest.mark.usefixtures("request_context")
def test_a_config_sync_without_any_users_revokes_no_oauth_grants() -> None:
    refresh_token = _start_grant(_DELETED)
    _write_users({})

    hooks.call("snapshot-pushed")

    assert _is_usable(refresh_token)


@pytest.mark.usefixtures("request_context")
def test_a_user_is_deleted_while_the_oauth_database_is_unavailable() -> None:
    _seed_users()
    OAUTH_DATABASE_BACKEND.path(OAUTH_DATABASE_NAME).unlink()

    _delete_user(_DELETED)

    assert _DELETED not in load_users()
