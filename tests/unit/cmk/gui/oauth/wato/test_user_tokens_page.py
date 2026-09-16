#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import AbstractContextManager
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.oauth.wato._user_tokens_page import UserOAuthTokensOverview
from cmk.gui.permissions import permission_registry
from cmk.gui.scopes import DEFAULT_SCOPE
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions


def _future(minutes: int) -> datetime:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).replace(microsecond=0)


def _register_client(name: str) -> str:
    with get_client_store() as store:
        registered = store.register([f"https://{name}.example/callback"], name)
    assert registered.is_ok()
    return registered.ok.client_id


@pytest.fixture(name="valid_csrf_token")
def fixture_valid_csrf_token() -> Iterator[None]:
    # The tests here build their POST by hand and don't carry a real CSRF
    # token, so the check is stubbed out. The real check is covered by
    # test_action_rejects_missing_csrf_token below.
    with patch("cmk.gui.oauth.wato._user_tokens_page.check_csrf_token"):
        yield


def _issue_token(user_id: UserId, client_id: str) -> str:
    with get_token_store() as store:
        token = store.issue_token(
            user_id, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=client_id
        )
    assert token.is_ok()
    return token.ok


def test_show_form_renders_only_the_callers_own_tokens(
    monkeypatch: pytest.MonkeyPatch, with_admin_login: UserId
) -> None:
    # page() renders the full Setup chrome via make_header(), which needs a
    # built frontend manifest that doesn't exist in the unit test environment
    # -- exercise the token table directly instead, same as _action() below.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)
    own_client = _register_client("own-client")
    other_client = _register_client("other-client")
    _issue_token(with_admin_login, own_client)
    _issue_token(UserId("other"), other_client)

    with output_funnel.plugged():
        UserOAuthTokensOverview()._show_form(request, Config())
        written = "".join(output_funnel.drain())

    assert "own-client" in written
    assert "other-client" not in written


@pytest.mark.usefixtures("with_admin_login")
def test_show_form_renders_empty_table_without_error() -> None:
    with output_funnel.plugged():
        UserOAuthTokensOverview()._show_form(request, Config())
        written = "".join(output_funnel.drain())

    assert "No entries" in written


@pytest.mark.usefixtures("valid_csrf_token")
def test_action_revokes_the_callers_own_token(with_admin_login: UserId) -> None:
    client_id = _register_client("client")
    token = _issue_token(with_admin_login, client_id)
    with get_token_store() as store:
        record = store.get_by_token(token)
    assert record is not None

    fake_request = MagicMock()
    fake_request.get_ascii_input.return_value = record.token_hash
    UserOAuthTokensOverview()._action(fake_request)

    with get_token_store() as store:
        assert store.get_by_token(token) is None


@pytest.mark.usefixtures("with_admin_login", "valid_csrf_token")
def test_action_does_not_revoke_another_users_token() -> None:
    client_id = _register_client("client")
    token = _issue_token(UserId("other"), client_id)
    with get_token_store() as store:
        record = store.get_by_token(token)
    assert record is not None

    fake_request = MagicMock()
    fake_request.get_ascii_input.return_value = record.token_hash
    UserOAuthTokensOverview()._action(fake_request)

    with get_token_store() as store:
        assert store.get_by_token(token) is not None


def _login(user_id: UserId, load_config: Config) -> AbstractContextManager[None]:
    # Unlike with_admin_login, this composes the login state *inside* a fresh
    # flask_app.test_request_context() -- with_admin_login's own session state
    # is bound to the ambient request context the fixture ran in, which does
    # not carry over into a new one, so the two tests below that need real
    # POST form data (for the bulk-checkbox parsing) can't rely on it.
    return login.TransactionIdContext(
        user_id, UserPermissions(load_config.roles, permission_registry, {user_id: ["admin"]}, [])
    )


@pytest.mark.usefixtures("valid_csrf_token")
def test_action_revokes_multiple_selected_tokens_at_once(
    flask_app: Flask,
    with_admin: tuple[UserId, str],
    load_config: Config,
) -> None:
    user_id = with_admin[0]
    client_id = _register_client("client")
    checked = _issue_token(user_id, client_id)
    unchecked = _issue_token(user_id, client_id)
    with get_token_store() as store:
        checked_record = store.get_by_token(checked)
        unchecked_record = store.get_by_token(unchecked)
    assert checked_record is not None
    assert unchecked_record is not None

    with (
        flask_app.test_request_context(
            method="POST",
            data={
                "_bulk_revoke_tokens": "1",
                f"_c_token_{checked_record.token_hash}": "on",
            },
        ),
        _login(user_id, load_config),
    ):
        flask_app.preprocess_request()
        UserOAuthTokensOverview()._action(request)

    with get_token_store() as store:
        assert store.get_by_token(checked) is None
        assert store.get_by_token(unchecked) is not None


@pytest.mark.usefixtures("valid_csrf_token")
def test_action_bulk_revoke_only_revokes_the_callers_own_tokens(
    flask_app: Flask,
    with_admin: tuple[UserId, str],
    load_config: Config,
) -> None:
    user_id = with_admin[0]
    client_id = _register_client("client")
    own_token = _issue_token(user_id, client_id)
    other_token = _issue_token(UserId("other"), client_id)
    with get_token_store() as store:
        own_record = store.get_by_token(own_token)
        other_record = store.get_by_token(other_token)
    assert own_record is not None
    assert other_record is not None

    with (
        flask_app.test_request_context(
            method="POST",
            data={
                "_bulk_revoke_tokens": "1",
                f"_c_token_{own_record.token_hash}": "on",
                f"_c_token_{other_record.token_hash}": "on",
            },
        ),
        _login(user_id, load_config),
    ):
        flask_app.preprocess_request()
        UserOAuthTokensOverview()._action(request)

    with get_token_store() as store:
        assert store.get_by_token(own_token) is None
        assert store.get_by_token(other_token) is not None


@pytest.mark.usefixtures("with_admin_login")
def test_action_rejects_missing_csrf_token() -> None:
    fake_request = MagicMock()
    fake_request.get_ascii_input.return_value = "irrelevant-hash"
    with pytest.raises(MKGeneralException, match="CSRF"):
        UserOAuthTokensOverview()._action(fake_request)
