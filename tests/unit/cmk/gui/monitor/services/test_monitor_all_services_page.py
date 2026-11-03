#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import urlparse

import pytest

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.monitor.command import DowntimeRecurrences, monitor_command_registry, MonitorCommands
from cmk.gui.monitor.services._pages._monitor_all_services import (
    _build_page_menu,
    _make_breadcrumb,
    MonitorAllServicesPage,
)
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions


@pytest.mark.usefixtures("user_without_permissions")
def test_page_denied_without_legacy_view_permission() -> None:
    page = MonitorAllServicesPage(MonitorCommands(monitor_command_registry), DowntimeRecurrences())

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


def _page_context() -> PageContext:
    return PageContext(
        config=Config(),
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(Config(), all_permissions()),
    )


@pytest.mark.usefixtures("with_user_login")
def test_breadcrumb_ends_with_this_page_linking_to_itself() -> None:
    last = list(_make_breadcrumb(_page_context()))[-1]

    assert last.title == "All services"
    assert last.url is not None
    assert urlparse(last.url).path == "monitor_all_services.py"


@pytest.mark.usefixtures("request_context")
def test_page_menu_drops_the_inline_help_entry() -> None:
    menu = _build_page_menu(Breadcrumb())

    assert "inline_help" not in [
        entry.name for topic in menu["help"].topics for entry in topic.entries
    ]
