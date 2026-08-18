#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The menus the "Services of host" page offers, and the page menu built from them.

The page shows the same "Host" and "Services" menus the legacy view does. It does not
derive them: the legacy side is injected as a source and read when the page asks, so this
domain neither reaches into the view layer nor has to keep a copy of what belongs there.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.type_defs import DynamicIcon, StaticIcon

from ._legacy_menu import LegacyHostMenu, LegacyHostMenuSource


@dataclass(frozen=True, kw_only=True)
class HostMenuEntry:
    """One entry of a menu: a name, a picture and where it leads."""

    ident: str | None
    title: str
    icon: StaticIcon | DynamicIcon
    url: str
    is_show_more: bool = False


@dataclass(frozen=True, kw_only=True)
class HostMenuTopic:
    title: str
    entries: Sequence[HostMenuEntry] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class HostMenu:
    ident: str
    title: str
    topics: Sequence[HostMenuTopic] = field(default_factory=tuple)


class HostMenus:
    """The menus a page about one host may offer beside its own.

    The legacy source is injected and read when a page asks, not copied at wiring time, so
    a visual registered later - by an edition or a user - is picked up without the wiring
    order mattering, and the two sides cannot drift apart.
    """

    def __init__(self) -> None:
        self._legacy: LegacyHostMenuSource | None = None

    def use_legacy_source(self, source: LegacyHostMenuSource) -> None:
        self._legacy = source

    def offered(self, *, hostname: str, site_id: str) -> Sequence[HostMenu]:
        """The menus to show for this host, empty while no source is wired."""
        if self._legacy is None:
            return ()
        return [
            self._adapt(menu)
            for menu in self._legacy.host_menus(hostname=hostname, site_id=site_id)
        ]

    @staticmethod
    def _adapt(menu: LegacyHostMenu) -> HostMenu:
        return HostMenu(
            ident=menu.ident,
            title=menu.title,
            topics=[
                HostMenuTopic(
                    title=topic.title,
                    entries=[
                        HostMenuEntry(
                            ident=entry.ident,
                            title=entry.title,
                            icon=entry.icon,
                            url=entry.url,
                            is_show_more=entry.is_show_more,
                        )
                        for entry in topic.entries
                    ],
                )
                for topic in menu.topics
            ],
        )


host_menus = HostMenus()


def build_page_menu(
    *,
    host_menus: HostMenus,
    hostname: str,
    site_id: str,
    breadcrumb: Breadcrumb,
) -> PageMenu:
    menu = PageMenu(
        dropdowns=[
            _as_dropdown(host_menu)
            for host_menu in host_menus.offered(hostname=hostname, site_id=site_id)
        ],
        breadcrumb=breadcrumb,
    )

    # PageMenu.__post_init__ appends the "display" and "help" dropdowns automatically.
    # "display" is kept: its only entry here is the kiosk-mode toggle, which the Vue
    # app does not provide and which is the only way back out of kiosk mode.
    # "help" is kept too, minus its "inline_help" entry - this page has no inline help.
    help_dropdown = menu["help"]
    for topic in help_dropdown.topics:
        topic.entries = [e for e in topic.entries if e.name != "inline_help"]

    return menu


def _as_dropdown(host_menu: HostMenu) -> PageMenuDropdown:
    return PageMenuDropdown(
        name=host_menu.ident,
        title=host_menu.title,
        topics=list(_as_topics(host_menu)),
    )


def _as_topics(host_menu: HostMenu) -> Iterator[PageMenuTopic]:
    for topic in host_menu.topics:
        yield PageMenuTopic(
            title=topic.title,
            entries=[
                PageMenuEntry(
                    name=entry.ident,
                    title=entry.title,
                    icon_name=entry.icon,
                    item=make_simple_link(entry.url),
                    is_show_more=entry.is_show_more,
                )
                for entry in topic.entries
            ],
        )
