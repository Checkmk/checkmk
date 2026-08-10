#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.monitor.hosts._pages._monitor_all_hosts import (
    _availability_dropdowns,
    MonitorAllHostsPage,
)
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.command.registry import command_registry
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


def test_page_denied_without_legacy_view_permission(user_without_permissions: UserId) -> None:
    page = MonitorAllHostsPage(command_registry)

    with pytest.raises(MKAuthException):
        page.page(PageContext(config=Config(), request=request))


def test_availability_dropdown_hidden_without_permission(
    user_without_permissions: UserId,
) -> None:
    assert _availability_dropdowns() == []


def test_availability_dropdown_shown_with_permission(with_user_login: UserId) -> None:
    assert [dropdown.name for dropdown in _availability_dropdowns()] == ["availability"]
