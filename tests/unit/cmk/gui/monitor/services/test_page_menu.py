#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.monitor.services._page_menu import build_page_menu, HostMenus
from cmk.gui.page_menu import PageMenuLink
from cmk.gui.type_defs import DynamicIcon, DynamicIconName, IconNames, StaticIcon


class _LegacyEntry:
    """Shaped like a legacy view's menu entry, without importing that layer."""

    def __init__(
        self,
        *,
        title: str,
        url: str,
        ident: str | None = None,
        icon: StaticIcon | DynamicIcon = DynamicIconName("status"),
        is_show_more: bool = False,
    ) -> None:
        self.ident = ident
        self.title = title
        self.icon = icon
        self.url = url
        self.is_show_more = is_show_more


class _LegacyTopic:
    """Shaped like a legacy view's menu topic, without importing that layer."""

    def __init__(self, *, title: str, entries: Sequence[_LegacyEntry]) -> None:
        self.title = title
        self.entries = entries


class _LegacyMenu:
    """Shaped like a legacy view's dropdown, without importing that layer."""

    def __init__(self, *, ident: str, title: str, topics: Sequence[_LegacyTopic]) -> None:
        self.ident = ident
        self.title = title
        self.topics = topics


class _LegacySource:
    """Stands in for the legacy side, which is injected, not copied."""

    def __init__(self, menus: list[_LegacyMenu]) -> None:
        self._menus = menus

    def add(self, menu: _LegacyMenu) -> None:
        self._menus.append(menu)

    def host_menus(self, *, hostname: str, site_id: str) -> Sequence[_LegacyMenu]:
        return self._menus


def _menu(ident: str = "host", *, entries: Sequence[_LegacyEntry] | None = None) -> _LegacyMenu:
    return _LegacyMenu(
        ident=ident,
        title=ident.title(),
        topics=[
            _LegacyTopic(
                title="Monitoring",
                entries=(
                    [_LegacyEntry(title="State of host", url="view.py?view_name=hoststatus")]
                    if entries is None
                    else entries
                ),
            )
        ],
    )


def _wired(*menus: _LegacyMenu) -> HostMenus:
    host_menus = HostMenus()
    host_menus.use_legacy_source(_LegacySource(list(menus)))
    return host_menus


def test_a_legacy_menu_is_adapted() -> None:
    offered = _wired(_menu()).offered(hostname="myhost", site_id="mysite")

    assert [(menu.ident, menu.title) for menu in offered] == [("host", "Host")]
    assert [topic.title for topic in offered[0].topics] == ["Monitoring"]
    assert [entry.url for topic in offered[0].topics for entry in topic.entries] == [
        "view.py?view_name=hoststatus"
    ]


def test_without_a_legacy_source_nothing_is_offered() -> None:
    assert HostMenus().offered(hostname="myhost", site_id="mysite") == ()


def test_a_menu_added_after_wiring_is_still_seen() -> None:
    """The source is read on demand, so wiring order must not matter."""
    source = _LegacySource([_menu("host")])
    host_menus = HostMenus()
    host_menus.use_legacy_source(source)

    source.add(_menu("services"))

    assert [menu.ident for menu in host_menus.offered(hostname="myhost", site_id="mysite")] == [
        "host",
        "services",
    ]


def test_an_entry_keeps_the_icon_the_legacy_side_named() -> None:
    """The icon travels as it is, so an emblem is not lost on the way here."""
    icon = StaticIcon(IconNames.folder, emblem="settings")
    offered = _wired(
        _menu(entries=[_LegacyEntry(title="Host configuration", url="wato.py", icon=icon)])
    ).offered(hostname="myhost", site_id="mysite")

    assert offered[0].topics[0].entries[0].icon == icon


def test_the_page_menu_carries_the_offered_menus_before_display_and_help(
    request_context: None,
) -> None:
    menu = build_page_menu(
        host_menus=_wired(_menu("host"), _menu("services")),
        hostname="myhost",
        site_id="mysite",
        breadcrumb=Breadcrumb(),
    )

    assert [dropdown.name for dropdown in menu.dropdowns] == [
        "host",
        "services",
        "display",
        "help",
    ]


def test_the_page_menu_links_each_entry_where_the_legacy_side_pointed(
    request_context: None,
) -> None:
    menu = build_page_menu(
        host_menus=_wired(
            _menu(entries=[_LegacyEntry(title="Availability", url="view.py?mode=availability")])
        ),
        hostname="myhost",
        site_id="mysite",
        breadcrumb=Breadcrumb(),
    )
    entry = menu["host"].topics[0].entries[0]

    assert isinstance(entry.item, PageMenuLink)
    assert entry.item.link.url == "view.py?mode=availability"


def test_the_page_menu_drops_the_inline_help_entry(request_context: None) -> None:
    menu = build_page_menu(
        host_menus=_wired(),
        hostname="myhost",
        site_id="mysite",
        breadcrumb=Breadcrumb(),
    )

    assert "inline_help" not in [
        entry.name for topic in menu["help"].topics for entry in topic.entries
    ]
