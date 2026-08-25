#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.monitor.command import (
    DowntimeRecurrences,
    monitor_command_registry,
    MonitorCommands,
)
from cmk.gui.monitor.services._page_menu import build_page_menu, HostMenus
from cmk.gui.monitor.services._pages._monitor_host_services import (
    _make_breadcrumb,
    _row_actions,
    MonitorHostServicesPage,
)
from cmk.gui.page_menu import PageMenu, PageMenuEntry, PageMenuLink
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from tests.testlib.gui.users import create_and_destroy_user


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
    page = MonitorHostServicesPage(
        MonitorCommands(monitor_command_registry), DowntimeRecurrences(), HostMenus()
    )

    with pytest.raises(MKAuthException):
        page.page(PageContext(config=Config(), request=request))


def _breadcrumb_of(host: str = "web-1", site: str = "local") -> Breadcrumb:
    ctx = PageContext(config=Config(), request=request)
    return _make_breadcrumb(
        ctx,
        HostName(host),
        SiteId(site),
        UserPermissions.from_config(ctx.config, permission_registry),
    )


def _url_of(breadcrumb: Breadcrumb, title: str) -> tuple[str, dict[str, list[str]]]:
    url = next(item.url for item in breadcrumb if item.title == title)
    assert url is not None
    parsed = urlparse(url)
    return parsed.path, parse_qs(parsed.query)


def _panel_of(breadcrumb: Breadcrumb, title: str) -> tuple[str, dict[str, list[str]]]:
    url = next(item.url for item in breadcrumb if item.title == title)
    assert url is not None
    parsed = urlparse(url)
    return parsed.path, parse_qs(parsed.fragment)


def test_breadcrumb_links_the_host_to_its_panel_in_the_all_hosts_listing(
    with_user_login: UserId,
) -> None:
    assert _panel_of(_breadcrumb_of(), "web-1") == (
        "monitor_all_hosts.py",
        {"host": ["web-1"], "site": ["local"]},
    )


def test_breadcrumb_falls_back_to_the_status_view_without_the_listing(
    user_without_permissions: UserId,
) -> None:
    assert _url_of(_breadcrumb_of(), "web-1") == (
        "view.py",
        {"view_name": ["hoststatus"], "host": ["web-1"], "site": ["local"]},
    )


def test_breadcrumb_names_the_host_between_all_hosts_and_this_page(
    with_user_login: UserId,
) -> None:
    assert [item.title for item in _breadcrumb_of()][-3:] == [
        "All hosts",
        "web-1",
        "Services of host",
    ]


def test_breadcrumb_keeps_this_page_reachable_from_its_own_item(with_user_login: UserId) -> None:
    assert _url_of(_breadcrumb_of(), "Services of host") == (
        "monitor_host_services.py",
        {"host": ["web-1"], "site": ["local"]},
    )


def test_breadcrumb_drops_all_hosts_without_permission_for_it(
    user_without_permissions: UserId,
) -> None:
    assert "All hosts" not in [item.title for item in _breadcrumb_of()]


def test_row_actions_link_the_parameters_of_the_service_in_the_row(with_user_login: UserId) -> None:
    config = Config()
    config.wato_enabled = True

    assert [(action.ident, action.url) for action in _row_actions(config, HostName("web-1"))] == [
        ("parameters", "wato.py?mode=object_parameters&host=web-1&service={service}")
    ]


def test_row_actions_are_dropped_where_setup_is_off(with_user_login: UserId) -> None:
    config = Config()
    config.wato_enabled = False

    assert _row_actions(config, HostName("web-1")) == []


def test_row_actions_are_dropped_without_the_rulesets_permission(
    user_without_permissions: UserId,
) -> None:
    config = Config()
    config.wato_enabled = True

    assert _row_actions(config, HostName("web-1")) == []


def _build_page_menu() -> PageMenu:
    # The menus themselves come from the injected legacy source, covered in test_page_menu.py.
    return build_page_menu(
        host_menus=HostMenus(),
        hostname="myhost",
        site_id="mysite",
        breadcrumb=Breadcrumb(),
    )


def _entry(menu: PageMenu, dropdown_name: str, entry_name: str) -> PageMenuEntry | None:
    return next(
        (
            entry
            for topic in menu[dropdown_name].topics
            for entry in topic.entries
            if entry.name == entry_name
        ),
        None,
    )


def test_display_dropdown_keeps_the_kiosk_toggle(with_admin_login: UserId) -> None:
    # The only entry of the "display" dropdown, and the only way out of kiosk mode.
    toggle = _entry(_build_page_menu(), "display", "hide_navigation")

    assert toggle is not None
    assert isinstance(toggle.item, PageMenuLink)
    assert "kiosk=true" in (toggle.item.link.url or "")
