#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato.pages.hosts import (
    PageAjaxAgentReceiverPort,
    PageAjaxDiagCmkAgent,
    PageAjaxPingHost,
)
from tests.unit.cmk.gui.users import create_and_destroy_user


@pytest.fixture(name="user_without_permissions")
def fixture_user_without_permissions(load_config: Config) -> Iterator[UserId]:
    with create_and_destroy_user(
        automation=False, role="no_permissions", config=load_config
    ) as created:
        user_id = created[0]
        with login.TransactionIdContext(
            user_id,
            UserPermissions(
                load_config.roles, permission_registry, {user_id: ["no_permissions"]}, []
            ),
        ):
            yield user_id


@pytest.mark.parametrize(
    "page",
    [PageAjaxPingHost(), PageAjaxDiagCmkAgent(), PageAjaxAgentReceiverPort()],
    ids=lambda p: type(p).__name__,
)
@pytest.mark.usefixtures("user_without_permissions")
def test_ajax_page_denied_without_permission(page: AjaxPage, mocker: MockerFixture) -> None:
    check_csrf_token = mocker.patch("cmk.gui.wato.pages.hosts.check_csrf_token")
    automation = mocker.patch("cmk.gui.wato.pages.hosts.make_automation_config")

    with pytest.raises(MKAuthException):
        page.page(PageContext(config=Config(), request=request))

    check_csrf_token.assert_called_once_with()
    automation.assert_not_called()
