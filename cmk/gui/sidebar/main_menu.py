#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu processing

Cares about the main navigation of our GUI. This is a) the small sidebar and b) the mega menu
"""
from typing import List, NamedTuple, Optional, Union

import cmk.gui.message as message
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.main_menu import any_show_more_items, mega_menu_registry
from cmk.gui.pages import AjaxPage, page_registry, PageResult, register
from cmk.gui.type_defs import Icon, MegaMenu, TopicMenuItem, TopicMenuTopic
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodInline
from cmk.gui.werks import may_acknowledge, num_unacknowledged_incompatible_werks


class MainMenuItem(NamedTuple):
    name: str
    title: str
    icon: Icon
    onopen: Optional[str]


class MainMenuRenderer:
    """Renders the main navigation sidebar"""

    def show(self) -> None:
        html.open_ul(id_="main_menu")
        self._show_main_menu_content()
        html.close_ul()

    def _show_main_menu_content(self) -> None:
        for menu_item in self._get_main_menu_items():
            if isinstance(menu_item.icon, dict):
                active_icon: Icon = {
                    "icon": menu_item.icon["icon"] + "_active",
                    "emblem": menu_item.icon["emblem"],
                }
            else:
                active_icon = menu_item.icon + "_active"

            html.open_li()
            html.popup_trigger(
                (self._get_popup_trigger_content(active_icon, menu_item)),
                ident="mega_menu_" + menu_item.name,
                method=MethodInline(self._get_mega_menu_content(menu_item)),
                cssclass=[menu_item.name],
                popup_group="main_menu_popup",
                hover_switch_delay=150,  # ms
                onopen=menu_item.onopen,
            )
            html.div(
                "",
                id_="popup_shadow",
                onclick="cmk.popup_menu.close_popup()",
                class_="min" if user.get_attribute("nav_hide_icons_title") else None,
            )
            html.close_li()

    def _get_popup_trigger_content(self, active_icon: Icon, menu_item: MainMenuItem) -> HTML:
        content = html.render_icon(menu_item.icon) + html.render_icon(
            active_icon, class_=["active"]
        )

        if not user.get_attribute("nav_hide_icons_title"):
            content += HTMLWriter.render_div(menu_item.title)

        return content

    def _get_main_menu_items(self) -> List[MainMenuItem]:
        items: List[MainMenuItem] = []
        for menu in sorted(mega_menu_registry.values(), key=lambda g: g.sort_index):
            if not menu.topics():
                continue  # Hide e.g. Setup menu when user is not permitted to see a single topic

            items.append(
                MainMenuItem(
                    name=menu.name,
                    title=str(menu.title),
                    icon=menu.icon,
                    onopen=menu.search.onopen if menu.search else None,
                )
            )
        return items

    def _get_mega_menu_content(self, menu_item: MainMenuItem) -> str:
        with output_funnel.plugged():
            menu = mega_menu_registry[menu_item.name]
            html.open_div(
                id_="popup_menu_%s" % menu_item.name,
                class_=(
                    ["popup_menu", "main_menu_popup"]
                    + (["min"] if user.get_attribute("nav_hide_icons_title") else [])
                ),
            )
            MegaMenuRenderer().show(menu)
            html.close_div()
            return output_funnel.drain()


@register("sidebar_message_read")
def ajax_message_read():
    response.set_content_type("application/json")
    try:
        message.delete_gui_message(request.var("id"))
        html.write_text("OK")
    except Exception:
        if active_config.debug:
            raise
        html.write_text("ERROR")


@page_registry.register_page("ajax_sidebar_get_messages")
class ModeAjaxSidebarGetMessages(AjaxPage):
    def page(self) -> PageResult:
        popup_msg: List = []
        hint_msg: int = 0

        for msg in message.get_gui_messages():
            if "gui_hint" in msg["methods"]:
                hint_msg += 1
            if "gui_popup" in msg["methods"]:
                popup_msg.append({"id": msg["id"], "text": msg["text"]})

        return {
            "popup_messages": popup_msg,
            "hint_messages": {
                "text": ungettext("message", "messages", hint_msg),
                "count": hint_msg,
            },
        }


@page_registry.register_page("ajax_sidebar_get_unack_incomp_werks")
class ModeAjaxSidebarGetUnackIncompWerks(AjaxPage):
    def page(self) -> PageResult:
        if not may_acknowledge():
            raise MKAuthException(_("You are not allowed to acknowlegde werks"))

        num_unack_werks = num_unacknowledged_incompatible_werks()
        tooltip_text = (
            ungettext(
                "%d unacknowledged incompatible werk",
                "%d unacknowledged incompatible werks",
                num_unack_werks,
            )
            % num_unack_werks
        )

        return {
            "count": num_unack_werks,
            "text": _("%d open incompatible werks") % num_unack_werks,
            "tooltip": tooltip_text,
        }


class MegaMenuRenderer:
    """Renders the content of the mega menu popups"""

    def show(self, menu: MegaMenu) -> None:
        more_id = "main_menu_" + menu.name

        show_more = user.get_show_more_setting(more_id)
        html.open_div(id_=more_id, class_=["main_menu", "more" if show_more else "less"])
        hide_entries_js = "cmk.popup_menu.mega_menu_hide_entries('%s')" % more_id

        html.open_div(class_="navigation_bar")
        html.open_div(class_="search_bar")
        if menu.search:
            menu.search.show_search_field()
        html.close_div()
        if menu.info_line:
            html.span(menu.info_line(), id_="info_line_%s" % menu.name, class_="info_line")
        topics = menu.topics()
        if any_show_more_items(topics):
            html.open_div()
            html.more_button(
                id_=more_id, dom_levels_up=3, additional_js=hide_entries_js, with_text=True
            )
            html.close_div()
        html.close_div()
        html.open_div(class_="content inner", id="content_inner_%s" % menu.name)
        for topic in topics:
            if not topic.items:
                continue
            self._show_topic(topic, menu.name)
        html.close_div()
        html.close_div()
        html.javascript(hide_entries_js)
        html.javascript("cmk.popup_menu.initialize_mega_menus();")
        html.open_div(class_="content inner", id="content_inner_%s_search" % menu.name)
        html.close_div()

    def _show_topic(self, topic: TopicMenuTopic, menu_id: str) -> None:
        show_more = all(i.is_show_more for i in topic.items)
        topic_id = "_".join(
            [menu_id, "topic", "".join(c.lower() for c in topic.title if not c.isspace())]
        )

        html.open_div(
            id_=topic_id,
            class_=["topic"] + (["show_more_mode"] if show_more else []),
            **{"data-max-entries": "%d" % topic.max_entries},
        )

        self._show_topic_title(menu_id, topic_id, topic)
        self._show_items(topic_id, topic)
        html.close_div()

    def _show_topic_title(self, menu_id: str, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_h2()
        html.open_a(
            class_="show_all_topics",
            href="",
            onclick="cmk.popup_menu.mega_menu_show_all_topics('%s')" % topic_id,
        )
        html.icon(icon="collapse_arrow", title=_("Show all %s topics") % menu_id)
        html.close_a()
        if not user.get_attribute("icons_per_item") and topic.icon:
            html.icon(topic.icon)
        html.span(topic.title)
        html.close_h2()

    def _show_items(self, topic_id: str, topic: TopicMenuTopic) -> None:
        html.open_ul()
        for item in sorted(topic.items, key=lambda g: g.sort_index):
            self._show_item(item)
        html.open_li(class_="show_all_items")
        html.open_a(href="", onclick="cmk.popup_menu.mega_menu_show_all_items('%s')" % topic_id)
        if user.get_attribute("icons_per_item"):
            html.icon("trans")
        html.write_text(_("Show all"))
        html.close_a()
        html.close_li()
        html.close_ul()

    def _show_item(self, item: TopicMenuItem) -> None:
        html.open_li(class_="show_more_mode" if item.is_show_more else None)
        html.open_a(
            href=item.url,
            target=item.target,
            onclick="cmk.popup_menu.close_popup()",
        )
        if user.get_attribute("icons_per_item"):
            html.icon(item.icon or "dash")
        self._show_item_title(item)
        html.close_a()
        html.close_li()

    def _show_item_title(self, item: TopicMenuItem) -> None:
        item_title: Union[HTML, str] = item.title
        if not item.button_title:
            html.write_text(item_title)
            return
        html.span(item.title)
        html.button(item.name, item.button_title)
