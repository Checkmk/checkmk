#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu processing

Cares about the main navigation of our GUI. This is a) the small sidebar and b) the mega menu
"""

from typing import NamedTuple, List

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar.quicksearch import QuicksearchSnapin
from cmk.gui.utils.popups import MethodInline

from cmk.gui.plugins.main_menu.utils import (
    mega_menu_registry,
    MegaMenu,
    TopicMenuTopic,
    TopicMenuItem,
)

MainMenuItem = NamedTuple("MainMenuItem", [
    ("name", str),
    ("title", str),
    ("icon_name", str),
])


class MainMenuRenderer:
    """Renders the main navigation sidebar"""
    def show(self) -> None:
        html.open_ul(id_="main_menu", class_=["mega_menu"])
        self._show_main_menu_content()
        html.close_ul()

    def _show_main_menu_content(self) -> None:
        html.open_li()
        html.popup_trigger(
            html.render_icon("main_search") + html.render_div(_("Search")),
            "mega_menu_search",
            method=MethodInline(self._get_search_menu_content()),
        )
        html.close_li()

        for menu_item in self._get_main_menu_items():
            html.open_li()
            html.popup_trigger(
                html.render_icon(menu_item.icon_name) + html.render_div(menu_item.title),
                ident="mega_menu_" + menu_item.name,
                method=MethodInline(self._get_mega_menu_content(menu_item)),
            )
            html.close_li()

    def _get_main_menu_items(self) -> List[MainMenuItem]:
        # TODO: Add permissions? For example WATO is not allowed for all users
        items: List[MainMenuItem] = []
        for menu in sorted(mega_menu_registry.values(), key=lambda g: g.sort_index):
            items.append(MainMenuItem(
                name=menu.name,
                title=menu.title,
                icon_name=menu.icon_name,
            ))
        return items

    # TODO(tb): can we use the MegaMenuRenderer here and move this code to mega_menu.py?
    def _get_search_menu_content(self) -> str:
        with html.plugged():
            html.open_div(class_=["popup_menu", "global_search"])
            QuicksearchSnapin().show()
            html.close_div()
            return html.drain()

    def _get_mega_menu_content(self, menu_item: MainMenuItem) -> str:
        with html.plugged():
            menu = mega_menu_registry[menu_item.name]
            html.open_div(class_="popup_menu")
            MegaMenuRenderer().show(menu)
            html.close_div()
            return html.drain()


class MegaMenuRenderer:
    """Renders the content of the mega menu popups"""
    def show(self, menu: MegaMenu) -> None:
        more_id = "main_menu_" + menu.name
        show_more = html.foldable_container_is_open("more_buttons", more_id, isopen=False)

        html.open_div(id_="main_menu_" + menu.name, class_=("more" if show_more else "less"))
        html.more_button(id_=more_id, dom_levels_up=1)
        html.open_div(class_="content inner")
        for topic in menu.topics():
            self._show_topic(topic, menu.name)
        html.close_div()
        html.close_div()

    def _show_topic(self, topic: TopicMenuTopic, menu_ident: str) -> None:
        advanced = all(i.is_advanced for i in topic.items)
        topic_id = "_".join(
            [menu_ident, "topic", "".join(c.lower() for c in topic.title if not c.isspace())])

        html.open_div(id_=topic_id, class_=["topic"] + (["advanced"] if advanced else []))

        self._show_topic_title(menu_ident, topic_id, topic)
        self._show_items(topic_id, topic)
        html.close_div()

    def _show_topic_title(self, menu_ident: str, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_h2()
        html.open_a(class_="show_all_topics",
                    href="",
                    onclick="cmk.popup_menu.mega_menu_show_all_topics('%s')" % topic_id)
        html.icon(title=_("Show all %s topics") % menu_ident, icon="collapse_arrow")
        html.close_a()
        # TODO: use one icon per topic or per item?
        if not config.user.get_attribute("ui_icons") and topic.icon_name:
            html.icon(title=None, icon=topic.icon_name)
        html.span(topic.title)
        html.close_h2()

    def _show_items(self, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_ul()
        counter = 0
        for item in topic.items:
            if counter < 10:
                self._show_item(item)
                if not item.is_advanced:
                    counter += 1
            else:
                self._show_item(item, extended=True)
        if counter >= 10:
            html.open_li(class_="show_all_items")
            html.hr()
            html.a(content=_("Show all"),
                   href="",
                   onclick="cmk.popup_menu.mega_menu_show_all_items('%s')" % topic_id)
            html.close_li()

        html.close_ul()

    def _show_item(self, item: TopicMenuItem, extended: bool = False) -> None:
        cls = ["advanced" if item.is_advanced else None, "extended" if extended else None]
        html.open_li(class_=cls)

        # TODO: Add description when needed
        # TODO: Add target when needed
        html.open_a(
            href=item.url,
            target="main",  # item.target or "main",
            onclick="cmk.popup_menu.close_popup()",
        )

        if config.user.get_attribute("ui_icons") and item.icon_name:
            html.icon(title=None, icon=item.icon_name)

        html.write_text(item.title)
        html.close_a()

        html.close_li()
