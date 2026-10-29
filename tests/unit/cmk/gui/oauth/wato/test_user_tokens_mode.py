#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.wato._user_tokens_mode import ModeOAuthTokens
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from tests.unit.cmk.gui.oauth.wato._token_helpers import _grant_id, _is_session_alive, _start_grant

_USER = UserId("cmkadmin")


def _register_client() -> str:
    with get_client_store() as store:
        registered = store.register(["https://client.example/callback"], "Example Client")
    assert registered.is_ok()
    return registered.ok.client_id


def _mode() -> ModeOAuthTokens:
    return ModeOAuthTokens()


def _run_action(
    flask_app: Flask,
    *,
    query_string: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
    valid_transaction: bool = True,
) -> None:
    with flask_app.test_request_context(
        method="POST",
        query_string={"mode": "oauth_tokens", **(query_string or {})},
        data=data,
    ):
        flask_app.preprocess_request()
        if valid_transaction:
            transactions.ignore()
            request.set_var("_transid", "-1")

        _mode().action(Config())


@pytest.mark.usefixtures("request_context")
def test_page_renders_every_users_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    # table_element() persists table options (sort/search state) to the acting
    # user's profile. The anonymous test session is LoggedInNobody, which
    # refuses to save a profile -- same workaround as test_table.py.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)
    client_id = _register_client()
    _start_grant(_USER, client_id)
    _start_grant(UserId("alice"), client_id)

    with output_funnel.plugged():
        _mode().page(Config())
        written = "".join(output_funnel.drain())

    assert _USER in written
    assert "alice" in written
    assert "Example Client" in written


@pytest.mark.usefixtures("request_context")
def test_page_renders_empty_table_without_error() -> None:
    with output_funnel.plugged():
        _mode().page(Config())
        written = "".join(output_funnel.drain())

    assert "No entries" in written


@pytest.mark.usefixtures("request_context")
class TestModeOAuthTokensAction:
    def test_removes_another_users_grant(self, flask_app: Flask) -> None:
        token = _start_grant(UserId("alice"), _register_client())

        _run_action(flask_app, query_string={"_delete": _grant_id(token)})

        assert not _is_session_alive(token)

    def test_bulk_removes_checked_grants_only(self, flask_app: Flask) -> None:
        client_id = _register_client()
        checked = _start_grant(_USER, client_id)
        unchecked = _start_grant(_USER, client_id)

        _run_action(
            flask_app,
            data={"_bulk_revoke_tokens": "1", f"_c_grant_{_grant_id(checked)}": "on"},
        )

        assert not _is_session_alive(checked)
        assert _is_session_alive(unchecked)

    def test_does_not_remove_when_transaction_is_invalid(self, flask_app: Flask) -> None:
        token = _start_grant(_USER, _register_client())

        _run_action(
            flask_app,
            query_string={"_delete": _grant_id(token)},
            valid_transaction=False,
        )

        assert _is_session_alive(token)
