#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import pytest
from flask import Flask

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.oauth.wato._user_tokens_mode import ModeOAuthTokens
from cmk.gui.pages import PageContext
from cmk.gui.scopes import DEFAULT_SCOPE
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions

_USER = UserId("cmkadmin")


def _future(minutes: int) -> datetime:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).replace(microsecond=0)


def _register_client() -> str:
    with get_client_store() as store:
        registered = store.register(["https://client.example/callback"], "Example Client")
    assert registered.is_ok()
    return registered.ok.client_id


def _issue_token(user_id: UserId, client_id: str) -> str:
    with get_token_store() as store:
        token = store.issue_token(
            user_id, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=client_id
        )
    assert token.is_ok()
    return token.ok


def test_static_permissions_returns_users_permission() -> None:
    assert ModeOAuthTokens.static_permissions() == ["users"]


@pytest.mark.usefixtures("request_context")
def test_page_renders_token_details(monkeypatch: pytest.MonkeyPatch, test_edition: Edition) -> None:
    # table_element() persists table options (sort/search state) to the acting
    # user's profile. The anonymous test session is LoggedInNobody, which
    # refuses to save a profile -- same workaround as test_table.py.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)  # noqa: ARG005
    client_id = _register_client()
    _issue_token(_USER, client_id)

    with output_funnel.plugged():
        ModeOAuthTokens(test_edition, PageContext(config=Config(), request=request)).page(Config())
        written = "".join(output_funnel.drain())

    assert _USER in written
    assert "Example Client" in written


@pytest.mark.usefixtures("request_context")
def test_page_renders_empty_table_without_error(test_edition: Edition) -> None:
    with output_funnel.plugged():
        ModeOAuthTokens(test_edition, PageContext(config=Config(), request=request)).page(Config())
        written = "".join(output_funnel.drain())

    assert "No entries" in written


@pytest.mark.usefixtures("request_context")
class TestModeOAuthTokensAction:
    def test_deletes_single_token(self, flask_app: Flask, test_edition: Edition) -> None:
        client_id = _register_client()
        token = _issue_token(_USER, client_id)
        with get_token_store() as store:
            record = store.get_by_token(token)
        assert record is not None

        with flask_app.test_request_context(
            method="POST",
            query_string={"mode": "oauth_tokens", "_delete": record.token_hash},
        ):
            flask_app.preprocess_request()
            transactions.ignore()
            request.set_var("_transid", "-1")

            ModeOAuthTokens(test_edition, PageContext(config=Config(), request=request)).action(
                Config()
            )

        with get_token_store() as store:
            assert store.get_by_token(token) is None

    def test_bulk_revokes_checked_tokens_only(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        client_id = _register_client()
        checked = _issue_token(_USER, client_id)
        unchecked = _issue_token(_USER, client_id)
        with get_token_store() as store:
            checked_record = store.get_by_token(checked)
            unchecked_record = store.get_by_token(unchecked)
        assert checked_record is not None
        assert unchecked_record is not None

        with flask_app.test_request_context(
            method="POST",
            data={
                "mode": "oauth_tokens",
                "_bulk_revoke_tokens": "1",
                f"_c_token_{checked_record.token_hash}": "on",
            },
        ):
            flask_app.preprocess_request()
            transactions.ignore()
            request.set_var("_transid", "-1")

            ModeOAuthTokens(test_edition, PageContext(config=Config(), request=request)).action(
                Config()
            )

        with get_token_store() as store:
            assert store.get_by_token(checked) is None
            assert store.get_by_token(unchecked) is not None

    def test_does_not_revoke_when_transaction_is_invalid(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        client_id = _register_client()
        token = _issue_token(_USER, client_id)
        with get_token_store() as store:
            record = store.get_by_token(token)
        assert record is not None

        with flask_app.test_request_context(
            method="POST",
            query_string={"mode": "oauth_tokens", "_delete": record.token_hash},
        ):
            flask_app.preprocess_request()

            ModeOAuthTokens(test_edition, PageContext(config=Config(), request=request)).action(
                Config()
            )

        with get_token_store() as store:
            assert store.get_by_token(token) is not None
