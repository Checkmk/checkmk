#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask

from cmk.ccc.version import Edition
from cmk.gui import oauth
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.oauth._registered_clients_mode import ModeRegisteredOAuthClients
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions


def test_static_permissions_returns_users_permission() -> None:
    assert ModeRegisteredOAuthClients.static_permissions() == ["users"]


@pytest.mark.usefixtures("request_context", "cleanup_registered_clients")
def test_page_renders_registered_client_details(
    monkeypatch: pytest.MonkeyPatch, test_edition: Edition
) -> None:
    # table_element() persists table options (sort/search state) to the acting
    # user's profile. The anonymous test session is LoggedInNobody, which
    # refuses to save a profile -- same workaround as test_table.py.
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda self: None)
    registered = oauth.client_store().register(
        ["https://client.example/callback", "https://client.example/other"],
        "Example Client",
    )

    with output_funnel.plugged():
        ModeRegisteredOAuthClients(test_edition).page(Config())
        written = "".join(output_funnel.drain())

    assert registered.client_id in written
    assert "Example Client" in written
    assert "https://client.example/callback" in written
    assert "https://client.example/other" in written
    assert str(registered.registered_at.year) in written


@pytest.mark.usefixtures("request_context")
def test_page_renders_empty_table_without_error(test_edition: Edition) -> None:
    with output_funnel.plugged():
        ModeRegisteredOAuthClients(test_edition).page(Config())
        written = "".join(output_funnel.drain())

    assert isinstance(written, str)


@pytest.mark.usefixtures("request_context")
class TestModeRegisteredOAuthClientsAction:
    def test_deletes_single_client(self, flask_app: Flask, test_edition: Edition) -> None:
        registered = oauth.client_store().register(["https://client.example/callback"], "Example")

        with flask_app.test_request_context(
            method="POST",
            query_string={
                "mode": "oauth_registered_clients",
                "_delete": registered.client_id,
            },
        ):
            flask_app.preprocess_request()
            transactions.ignore()
            request.set_var("_transid", "-1")

            ModeRegisteredOAuthClients(test_edition).action(Config())

        assert oauth.client_store().get(registered.client_id) is None

    @pytest.mark.usefixtures("cleanup_registered_clients")
    def test_bulk_deletes_checked_clients_only(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        checked = oauth.client_store().register(["https://client.example/checked"], "Checked")
        unchecked = oauth.client_store().register(["https://client.example/unchecked"], "Unchecked")

        with flask_app.test_request_context(
            method="POST",
            data={
                "mode": "oauth_registered_clients",
                "_bulk_delete_clients": "1",
                f"_c_client_{checked.client_id}": "on",
            },
        ):
            flask_app.preprocess_request()
            transactions.ignore()
            request.set_var("_transid", "-1")

            ModeRegisteredOAuthClients(test_edition).action(Config())

        assert oauth.client_store().get(checked.client_id) is None
        assert oauth.client_store().get(unchecked.client_id) == unchecked

    @pytest.mark.usefixtures("cleanup_registered_clients")
    def test_does_not_delete_when_transaction_is_invalid(
        self, flask_app: Flask, test_edition: Edition
    ) -> None:
        registered = oauth.client_store().register(["https://client.example/callback"], "Example")

        with flask_app.test_request_context(
            method="POST",
            query_string={
                "mode": "oauth_registered_clients",
                "_delete": registered.client_id,
            },
        ):
            flask_app.preprocess_request()

            ModeRegisteredOAuthClients(test_edition).action(Config())

        assert oauth.client_store().get(registered.client_id) == registered
