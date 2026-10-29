#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.wato._user_tokens_mode import ModeOAuthTokens
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from tests.unit.cmk.gui.oauth.wato._token_helpers import _grant_id, _is_session_alive, _start_grant

_USER = UserId("cmkadmin")


def _register_client() -> str:
    with get_client_store() as store:
        registered = store.register(["https://client.example/callback"], "Example Client")
    assert registered.is_ok()
    return registered.ok.client_id


def _mode(edition: Edition) -> ModeOAuthTokens:
    return ModeOAuthTokens(
        edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )


def _run_action(
    flask_app: Flask,
    edition: Edition,
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

        _mode(edition).action(Config())


@pytest.mark.usefixtures("request_context")
def test_page_renders_every_users_grants(
    monkeypatch: pytest.MonkeyPatch, test_edition: Edition
) -> None:
    # table_element() persists table options (sort/search state) to the acting
    # user's profile. The anonymous test session is LoggedInNobody, which
    # refuses to save a profile -- same workaround as test_table.py.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)  # noqa: ARG005
    client_id = _register_client()
    _start_grant(_USER, client_id)
    _start_grant(UserId("alice"), client_id)

    with output_funnel.plugged():
        _mode(test_edition).page(Config())
        written = "".join(output_funnel.drain())

    assert _USER in written
    assert "alice" in written
    assert "Example Client" in written


@pytest.mark.usefixtures("request_context")
def test_page_renders_empty_table_without_error(test_edition: Edition) -> None:
    with output_funnel.plugged():
        _mode(test_edition).page(Config())
        written = "".join(output_funnel.drain())

    assert "No entries" in written


@pytest.mark.usefixtures("request_context")
class TestModeOAuthTokensAction:
    def test_removes_another_users_grant(self, flask_app: Flask, test_edition: Edition) -> None:
        token = _start_grant(UserId("alice"), _register_client())

        _run_action(flask_app, test_edition, query_string={"_delete": _grant_id(token)})

        assert not _is_session_alive(token)

    def test_bulk_removes_checked_grants_only(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        client_id = _register_client()
        checked = _start_grant(_USER, client_id)
        unchecked = _start_grant(_USER, client_id)

        _run_action(
            flask_app,
            test_edition,
            data={"_bulk_revoke_tokens": "1", f"_c_grant_{_grant_id(checked)}": "on"},
        )

        assert not _is_session_alive(checked)
        assert _is_session_alive(unchecked)

    def test_does_not_remove_when_transaction_is_invalid(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        token = _start_grant(_USER, _register_client())

        _run_action(
            flask_app,
            test_edition,
            query_string={"_delete": _grant_id(token)},
            valid_transaction=False,
        )

        assert _is_session_alive(token)
