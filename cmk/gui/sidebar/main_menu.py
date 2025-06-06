#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu processing

Cares about the main navigation of our GUI. This is a) the small sidebar and b) the mega menu
"""

from typing import NamedTuple, TypedDict

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui import message
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.main_menu import any_show_more_items, mega_menu_registry
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import Icon, MegaMenu, TopicMenuItem, TopicMenuTopic, TopicMenuTopicSegment
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodInline
from cmk.gui.werks import may_acknowledge, num_unacknowledged_incompatible_werks


class MainMenuItem(NamedTuple):
    name: str
    title: str
    icon: Icon
    onopen: str | None


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

    def _get_main_menu_items(self) -> list[MainMenuItem]:
        items: list[MainMenuItem] = []
        for menu in sorted(mega_menu_registry.values(), key=lambda g: g.sort_index):
            if not menu.topics():
                continue  # Hide e.g. Setup menu when user is not permitted to see a single topic

            if menu.hide():
                continue

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


def ajax_message_read():
    response.set_content_type("application/json")
    try:
        message.delete_gui_message(request.get_str_input_mandatory("id"))
        html.write_text_permissive("OK")
    except Exception:
        if active_config.debug:
            raise
        html.write_text_permissive("ERROR")


class PopUpMessage(TypedDict):
    id: str
    text: str


class PageAjaxSidebarGetMessages(AjaxPage):
    def page(self) -> PageResult:
        popup_msg: list[PopUpMessage] = []
        hint_msg: int = 0

        for msg in message.get_gui_messages():
            if "gui_hint" in msg["methods"] and not msg.get("acknowledged"):
                hint_msg += 1
            if "gui_popup" in msg["methods"]:
                popup_msg.append(PopUpMessage(id=msg["id"], text=msg["text"]["content"]))

        return {
            "popup_messages": popup_msg,
            "hint_messages": {
                "title": _("User message"),
                "text": _("new"),
                "count": hint_msg,
            },
        }


class PageAjaxSidebarGetUnackIncompWerks(AjaxPage):
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
                id_=more_id,
                dom_levels_up=3,
                additional_js=hide_entries_js,
                with_text=True,
            )
            html.close_div()
        html.close_div()
        html.open_div(class_="content inner", id="content_inner_%s" % menu.name)
        for topic in topics:
            if not topic.entries:
                continue
            self._show_topic(topic, menu.name)
        html.close_div()
        html.close_div()
        html.javascript(hide_entries_js)
        html.javascript("cmk.popup_menu.initialize_mega_menus();")
        html.open_div(class_="content inner", id="content_inner_%s_search" % menu.name)
        html.close_div()

    def _get_topic_id(self, menu_id: str, topic_title: str) -> str:
        return "_".join(
            [
                menu_id,
                "topic",
                "".join(c.lower() for c in topic_title if not c.isspace()),
            ]
        )

    def _show_topic(
        self,
        topic: TopicMenuTopic | TopicMenuTopicSegment,
        menu_id: str,
    ) -> None:
        show_more = all(i.is_show_more for i in topic.entries)
        topic_id = self._get_topic_id(menu_id, topic.title)
        is_multilevel: bool = (
            isinstance(topic, TopicMenuTopicSegment) and topic.mode == "multilevel"
        )

        html.open_div(
            id_=topic_id,
            class_=["topic"]
            + (["show_more_mode"] if show_more else [])
            + (["multilevel_topic_segment"] if is_multilevel else []),
            **{"data-max-entries": "%d" % topic.max_entries},
        )

        self._show_topic_title(menu_id, topic_id, topic)
        multilevel_topics: list[TopicMenuTopicSegment] = self._show_items(menu_id, topic_id, topic)
        html.close_div()

        for multilevel_topic in multilevel_topics:
            self._show_topic(multilevel_topic, menu_id)

    def _show_topic_title(
        self,
        menu_id: str,
        topic_id: str,
        topic: TopicMenuTopic | TopicMenuTopicSegment,
    ) -> None:
        html.open_h2()
        html.open_a(
            class_="collapse_topic",
            href=None,
            onclick="cmk.popup_menu.mega_menu_collapse_topic('%s')" % topic_id,
        )
        html.icon(
            icon="collapse_arrow",
            title=(
                _("Show all %s topics") % menu_id
                if isinstance(topic, TopicMenuTopic)
                else _("Close topic segment %s") % topic.title
            ),
        )
        html.close_a()
        if not user.get_attribute("icons_per_item") and topic.icon:
            html.icon(topic.icon)
        html.span(topic.title)
        html.close_h2()

    def _show_items(
        self, menu_id: str, topic_id: str, topic: TopicMenuTopic | TopicMenuTopicSegment
    ) -> list[TopicMenuTopicSegment]:
        html.open_ul()
        multilevel_topics: list[TopicMenuTopicSegment] = []
        for entry in sorted(topic.entries, key=lambda g: g.sort_index):
            if isinstance(entry, TopicMenuTopicSegment):
                if entry.mode == "multilevel":
                    self._show_multilevel_item(entry, menu_id)
                    multilevel_topics.append(entry)
                elif entry.mode == "indented":
                    self._show_indented_topic_segment(entry)
                else:
                    raise MKGeneralException(
                        f"Main menu entry.mode '{entry.mode}' is not implemented"
                    )
            else:
                self._show_item(entry)
        html.open_li(class_="show_all_items")
        html.open_a(
            href=None,
            onclick="cmk.popup_menu.mega_menu_show_all_items('%s')" % topic_id,
        )
        if user.get_attribute("icons_per_item"):
            html.icon("trans")
        html.write_text_permissive(_("Show all"))
        html.close_a()
        html.close_li()
        html.close_ul()

        return multilevel_topics

    def _show_multilevel_item(self, multilevel_topic: TopicMenuTopicSegment, menu_id: str) -> None:
        multilevel_topic_id = self._get_topic_id(menu_id, multilevel_topic.title)
        html.open_li(class_="multilevel_item")
        html.open_a(
            href="javascript:void(0);",
            onclick="cmk.popup_menu.mega_menu_show_all_items('%s')" % multilevel_topic_id,
            title=_("Show entries for %s") % multilevel_topic.title,
        )
        if user.get_attribute("icons_per_item"):
            html.icon(multilevel_topic.icon or "dash")
        html.open_span()
        self._show_item_title(multilevel_topic)
        html.close_span()
        html.img(
            src=theme.url("images/tree_closed.svg"),
        )
        html.close_a()
        html.close_li()

    def _show_indented_topic_segment(self, topic_segment: TopicMenuTopicSegment) -> None:
        html.open_ul(
            class_="indented_topic_segment"
            + (" show_more_mode" if topic_segment.is_show_more else "")
        )
        html.span(topic_segment.title)
        for item in sorted(topic_segment.entries, key=lambda g: g.sort_index):
            # We only allow for one level of indentation so far
            assert isinstance(item, TopicMenuItem)
            self._show_item(item)
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

    def _show_item_title(self, item: TopicMenuItem | TopicMenuTopicSegment) -> None:
        item_title: HTML | str = item.title
        if isinstance(item, TopicMenuTopicSegment) or not item.button_title:
            html.write_text_permissive(item_title)
            return
        html.span(item.title)
        html.button(item.name, item.button_title)
