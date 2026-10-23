#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.monitor.command import (
    DowntimeRecurrences,
    monitor_command_registry,
    MonitorCommands,
)
from cmk.gui.monitor.hosts._pages._monitor_all_hosts import (
    _availability_dropdowns,
    MonitorAllHostsPage,
)
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions


@pytest.mark.usefixtures("user_without_permissions")
def test_page_denied_without_legacy_view_permission() -> None:
    page = MonitorAllHostsPage(MonitorCommands(monitor_command_registry), DowntimeRecurrences())

    with pytest.raises(MKAuthException):
        page.page(
            PageContext(
                config=Config(),
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(Config(), all_permissions()),
            )
        )


@pytest.mark.usefixtures("user_without_permissions")
def test_availability_dropdown_hidden_without_permission() -> None:
    assert _availability_dropdowns() == []


@pytest.mark.usefixtures("with_user_login")
def test_availability_dropdown_shown_with_permission() -> None:
    assert [dropdown.name for dropdown in _availability_dropdowns()] == ["availability"]
