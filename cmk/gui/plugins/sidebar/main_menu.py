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
from cmk.gui.type_defs import (
    MegaMenu,
    TopicMenuTopic,
    TopicMenuItem,
)

from cmk.gui.main_menu import (
    mega_menu_registry,
    any_advanced_items,
)

MainMenuItem = NamedTuple("MainMenuItem", [
    ("name", str),
    ("title", str),
    ("icon_name", str),
])


def get_show_more_setting(more_id: str) -> bool:
    if config.user.get_attribute("ui_basic_advanced_mode") == "enforce_advanced":
        return True

    if config.user.get_attribute("ui_basic_advanced_mode") == "enforce_basic":
        return False

    return html.foldable_container_is_open(
        treename="more_buttons",
        id_=more_id,
        isopen=config.user.get_attribute("ui_basic_advanced_mode") == "default_advanced")


class MainMenuRenderer:
    """Renders the main navigation sidebar"""
    def show(self) -> None:
        html.open_ul(id_="main_menu")
        self._show_main_menu_content()
        html.close_ul()

    def _show_main_menu_content(self) -> None:
        html.open_li()
        html.popup_trigger(
            html.render_icon("main_search") + html.render_div(_("Search")),
            "mega_menu_search",
            method=MethodInline(self._get_search_menu_content()),
            popup_group="main_menu_popup",
        )
        html.close_li()

        for menu_item in self._get_main_menu_items():
            html.open_li()
            html.popup_trigger(
                html.render_icon(menu_item.icon_name) + html.render_div(menu_item.title),
                ident="mega_menu_" + menu_item.name,
                method=MethodInline(self._get_mega_menu_content(menu_item)),
                cssclass=menu_item.name,
                popup_group="main_menu_popup",
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
            html.open_div(class_=["popup_menu", "main_menu_popup", "global_search"])
            QuicksearchSnapin().show()
            html.close_div()
            html.div("", id_="popup_shadow", onclick="cmk.popup_menu.close_popup()")
            return html.drain()

    def _get_mega_menu_content(self, menu_item: MainMenuItem) -> str:
        with html.plugged():
            menu = mega_menu_registry[menu_item.name]
            html.open_div(class_=["popup_menu", "main_menu_popup"])
            MegaMenuRenderer().show(menu)
            html.close_div()
            html.div("", id_="popup_shadow", onclick="cmk.popup_menu.close_popup()")
            return html.drain()


class MegaMenuRenderer:
    """Renders the content of the mega menu popups"""
    def show(self, menu: MegaMenu) -> None:
        more_id = "main_menu_" + menu.name

        show_more = get_show_more_setting(more_id)
        html.open_div(id_=more_id, class_=["main_menu", "more" if show_more else "less"])
        hide_entries_js = "cmk.popup_menu.mega_menu_hide_entries('%s')" % more_id

        html.open_div(class_="navigation_bar")
        html.div("", class_="search_bar")
        topics = menu.topics()
        if any_advanced_items(topics):
            html.open_div()
            html.more_button(id_=more_id,
                             dom_levels_up=3,
                             additional_js=hide_entries_js,
                             with_text=True)
            html.close_div()
        html.close_div()
        html.open_div(class_="content inner")
        for topic in topics:
            self._show_topic(topic, menu.name)
        html.div(None, class_="sentinel")
        html.close_div()
        html.close_div()
        html.javascript(hide_entries_js)
        html.javascript("cmk.popup_menu.initialize_mega_menus();")

    def _show_topic(self, topic: TopicMenuTopic, menu_id: str) -> None:
        advanced = all(i.is_advanced for i in topic.items)
        topic_id = "_".join(
            [menu_id, "topic", "".join(c.lower() for c in topic.title if not c.isspace())])

        html.open_div(id_=topic_id, class_=["topic"] + (["advanced"] if advanced else []))

        self._show_topic_title(menu_id, topic_id, topic)
        self._show_items(topic_id, topic)
        html.close_div()

    def _show_topic_title(self, menu_id: str, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_h2()
        html.open_a(class_="show_all_topics",
                    href="",
                    onclick="cmk.popup_menu.mega_menu_show_all_topics('%s')" % topic_id)
        html.icon(icon="collapse_arrow", title=_("Show all %s topics") % menu_id)
        html.close_a()
        if not config.user.get_attribute("icons_per_item") and topic.icon_name:
            html.icon(topic.icon_name)
        html.span(topic.title)
        html.close_h2()

    def _show_items(self, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_ul()
        for item in topic.items:
            self._show_item(item)
        html.open_li(class_="show_all_items")
        html.hr()
        html.a(content=_("Show all"),
               href="",
               onclick="cmk.popup_menu.mega_menu_show_all_items('%s')" % topic_id)
        html.close_li()
        html.close_ul()

    def _show_item(self, item: TopicMenuItem) -> None:
        html.open_li(class_="advanced" if item.is_advanced else None)
        html.open_a(
            href=item.url,
            target="main",
            onclick="cmk.popup_menu.close_popup()",
        )
        if config.user.get_attribute("icons_per_item") and item.icon_name:
            html.icon(item.icon_name, emblem=item.emblem)
        html.write_text(item.title)
        html.close_a()
        html.close_li()
