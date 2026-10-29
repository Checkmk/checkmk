#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import AbstractContextManager
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.http import Request, request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.wato._user_tokens_page import UserOAuthTokensOverview
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from tests.unit.cmk.gui.oauth.wato._token_helpers import _grant_id, _is_session_alive, _start_grant


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


def _remove_one(edition: Edition, grant_id: str) -> None:
    fake_request = Mock(spec=Request)
    fake_request.get_ascii_input.return_value = grant_id
    UserOAuthTokensOverview(edition)._action(fake_request)  # noqa: SLF001


def test_show_form_renders_only_the_callers_own_grants(
    monkeypatch: pytest.MonkeyPatch, test_edition: Edition, with_admin_login: UserId
) -> None:
    # page() renders the full Setup chrome via make_header(), which needs a
    # built frontend manifest that doesn't exist in the unit test environment
    # -- exercise the token table directly instead, same as _action() below.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)  # noqa: ARG005
    own_client = _register_client("own-client")
    other_client = _register_client("other-client")
    _start_grant(with_admin_login, own_client)
    _start_grant(UserId("other"), other_client)

    with output_funnel.plugged():
        UserOAuthTokensOverview(test_edition)._show_form(request, Config())  # noqa: SLF001
        written = "".join(output_funnel.drain())

    assert "own-client" in written
    assert "other-client" not in written


@pytest.mark.usefixtures("with_admin_login")
def test_show_form_renders_empty_table_without_error(test_edition: Edition) -> None:
    with output_funnel.plugged():
        UserOAuthTokensOverview(test_edition)._show_form(request, Config())  # noqa: SLF001
        written = "".join(output_funnel.drain())

    assert "No entries" in written


@pytest.mark.usefixtures("valid_csrf_token")
def test_action_removes_the_callers_own_grant(
    test_edition: Edition, with_admin_login: UserId
) -> None:
    token = _start_grant(with_admin_login, _register_client("client"))

    _remove_one(test_edition, _grant_id(token))

    assert not _is_session_alive(token)


def _login(user_id: UserId, load_config: Config) -> AbstractContextManager[None]:
    # Unlike with_admin_login, this composes the login state *inside* a fresh
    # flask_app.test_request_context() -- with_admin_login's own session state
    # is bound to the ambient request context the fixture ran in, which does
    # not carry over into a new one, so the two tests below that need real
    # POST form data (for the bulk-checkbox parsing) can't rely on it.
    return login.TransactionIdContext(
        user_id,
        UserPermissions(
            load_config.roles,
            all_permissions(),
            {user_id: ["admin"]},
            [],
        ),
    )


def _bulk_remove(
    flask_app: Flask,
    edition: Edition,
    user_id: UserId,
    load_config: Config,
    *grant_ids: str,
) -> None:
    with (
        flask_app.test_request_context(
            method="POST",
            data={
                "_bulk_revoke_tokens": "1",
                **{f"_c_grant_{grant_id}": "on" for grant_id in grant_ids},
            },
        ),
        _login(user_id, load_config),
    ):
        flask_app.preprocess_request()
        UserOAuthTokensOverview(edition)._action(request)  # noqa: SLF001


@pytest.mark.usefixtures("valid_csrf_token")
def test_action_bulk_remove_ends_only_the_callers_own_checked_grants(
    flask_app: Flask,
    test_edition: Edition,
    with_admin: tuple[UserId, str],
    load_config: Config,
) -> None:
    user_id = with_admin[0]
    client_id = _register_client("client")
    checked = _start_grant(user_id, client_id)
    unchecked = _start_grant(user_id, client_id)
    others = _start_grant(UserId("other"), client_id)

    _bulk_remove(
        flask_app, test_edition, user_id, load_config, _grant_id(checked), _grant_id(others)
    )

    assert not _is_session_alive(checked)
    assert _is_session_alive(unchecked)
    assert _is_session_alive(others)


@pytest.mark.usefixtures("with_admin_login")
def test_action_rejects_missing_csrf_token(test_edition: Edition) -> None:
    fake_request = Mock(spec=Request)
    fake_request.get_ascii_input.return_value = "irrelevant-hash"
    fake_request.remote_ip = "127.0.0.1"
    with pytest.raises(MKGeneralException, match="CSRF"):
        UserOAuthTokensOverview(test_edition)._action(fake_request)  # noqa: SLF001
