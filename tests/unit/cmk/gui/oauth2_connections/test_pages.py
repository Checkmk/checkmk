#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import EnvironBuilder

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.oauth2_connections.wato import _modes as oauth2_modes
from cmk.gui.oauth2_connections.wato._pages import PageRequestAndSaveMsGraphAccessToken
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions


def _page_context(data: str, content_type: str) -> PageContext:
    return PageContext(
        config=Config(),
        request=Request(
            EnvironBuilder(method="POST", data=data, content_type=content_type).get_environ()
        ),
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(Config(), all_permissions()),
    )


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_access_token_request_without_json_is_a_user_error() -> None:
    with pytest.raises(MKUserError):
        PageRequestAndSaveMsGraphAccessToken().page(_page_context("x", "text/plain"))


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_access_token_request_without_form_data_is_a_user_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(oauth2_modes, "get_configured_site_choices", list)

    with pytest.raises(MKUserError):
        PageRequestAndSaveMsGraphAccessToken().page(_page_context("{}", "application/json"))
