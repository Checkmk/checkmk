#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu processing

Cares about the main navigation of our GUI. This is a) the small sidebar and b) the main menu
"""

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="unreachable"

import dataclasses
from typing import override, TypedDict

from cmk.gui import message
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request, response
from cmk.gui.i18n import _, ungettext
from cmk.gui.icon_helpers import migrate_to_dynamic_icon
from cmk.gui.logged_in import user
from cmk.gui.main_menu import any_show_more_items, main_menu_registry
from cmk.gui.main_menu_types import ConfigurableMainMenuItem, MainMenuItem, MainMenuLinkItem
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.search_menu import get_unified_search_props
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.misc import validate_uuid_str
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.werks import may_acknowledge, num_unacknowledged_incompatible_werks
from cmk.shared_typing.main_menu import (
    MainMenuConfig,
    NavItem,
    NavItemHeader,
    NavItemIdEnum,
    NavItemShowMore,
    NavItemTopic,
    NavItemTopicEntry,
    NavLinkItem,
    StartItem,
    TopicItemMode,
)
from cmk.shared_typing.unified_search import Provider, ProviderName, UnifiedSearchProps


class MainMenuConfigCreator:
    user_permissions: UserPermissions
    request: Request
    search_config: UnifiedSearchProps

    def __init__(self, user_permissions: UserPermissions, request: Request):
        self.user_permissions = user_permissions
        self.request = request
        self.search_config = get_unified_search_props(self.request)

    def create(self, start_url: str, home_icon_path: str | None) -> MainMenuConfig:
        search_item = main_menu_registry.menu_search()
        # collecting the items also adjusts the self.search_config
        main_items = self._get_menu_items(is_user_nav=False)
        user_items = self._get_menu_items(is_user_nav=True)

        if callable(search_item.get_vue_app):
            search_vue_app = search_item.get_vue_app(self.request)
            search_vue_app = dataclasses.replace(
                search_vue_app, data=dataclasses.asdict(self.search_config)
            )
            search_item = dataclasses.replace(search_item, vue_app=search_vue_app)

        for i, item in enumerate(main_items):
            if item.id == NavItemIdEnum.search:
                main_items[i] = self._get_nav_item_from_main_menu_item(search_item)
                break

        return MainMenuConfig(
            hide_item_title=user.get_attribute("nav_hide_icons_title") == "hide",
            start=StartItem(
                title=_("Go to main page"),
                url=user.start_url or start_url,
                icon_path=home_icon_path,
            ),
            main=main_items,
            user=user_items,
        )

    def _get_menu_items(self, is_user_nav: bool) -> list[NavItem | NavLinkItem]:
        items: list[NavItem | NavLinkItem] = []

        for menu in sorted(main_menu_registry.values(), key=lambda g: g.sort_index):
            if menu.is_user_nav != is_user_nav:
                continue

            if isinstance(menu, ConfigurableMainMenuItem):
                menu = menu.get_item_instance(menu, user)

            if isinstance(menu, MainMenuItem):
                if not menu.topics and menu.get_topics:
                    menu = dataclasses.replace(
                        menu, topics=list(menu.get_topics(self.user_permissions))
                    )

                if not menu.vue_app and menu.get_vue_app:
                    menu = dataclasses.replace(menu, vue_app=menu.get_vue_app(self.request))

                if not menu.topics and not menu.vue_app:
                    continue  # Hide e.g. Setup menu when user is not permitted to see a single topic

            if menu.hide and menu.hide():
                continue

            self._add_unified_searchprovider(menu)

            items.append(
                self._get_nav_item_from_main_menu_item(
                    menu=menu,
                )
            )
        return items

    def _get_nav_item_from_main_menu_item(
        self, menu: MainMenuItem | MainMenuLinkItem
    ) -> NavItem | NavLinkItem:
        if isinstance(menu, NavItem):
            has_show_more = any_show_more_items(list(menu.topics)) if menu.topics else False

            if has_show_more:
                more_id = "main_menu_" + menu.id
                show_more = user.get_show_more_setting(more_id)

            return NavItem(
                id=NavItemIdEnum(menu.id),
                title=str(menu.title),
                sort_index=menu.sort_index,
                topics=self._get_topics_of_menu(menu) or None,
                set_focus_on_element_by_id=menu.set_focus_on_element_by_id,
                vue_app=menu.vue_app or menu.get_vue_app(self.request)
                if callable(menu.get_vue_app)
                else None,
                header=NavItemHeader(
                    info=menu.info_line() if menu.info_line else None,
                    show_more=has_show_more,
                    trigger_button=menu.header.trigger_button,
                )
                if menu.header
                else None,
                shortcut=menu.shortcut,
                show_more=NavItemShowMore(active=show_more) if has_show_more else None,
                popup_small=menu.popup_small,
                hint=str(menu.hint),
                badge=menu.badge,
            )

        return NavLinkItem(
            id=NavItemIdEnum(menu.id),
            title=str(menu.title),
            sort_index=menu.sort_index,
            url=menu.url or menu.get_url(self.request) if callable(menu.get_url) else None,
            target=menu.target,
            shortcut=menu.shortcut,
            hint=str(menu.hint),
            badge=menu.badge,
        )

    def _get_topics_of_menu(self, menu: MainMenuItem) -> list[NavItemTopic]:
        if not menu.topics:
            return []

        return [
            NavItemTopic(
                id=topic.id,
                title=topic.title,
                icon=migrate_to_dynamic_icon(topic.icon)
                if not user.get_attribute("icons_per_item")
                else None,
                entries=self._get_entries_of_topic(topic),
                is_show_more=topic.is_show_more,
                sort_index=topic.sort_index,
            )
            for topic in menu.topics
        ]

    def _get_entries_of_topic(
        self, topic: NavItemTopic | NavItemTopicEntry
    ) -> list[NavItemTopicEntry]:
        if not topic.entries:
            return []

        return [
            NavItemTopicEntry(
                id=entry.id,
                title=entry.title,
                mode=entry.mode,
                url=None,
                target=None,
                is_show_more=None,
                icon=None,
                toggle=None,
                chip=None,
                sort_index=entry.sort_index,
                entries=self._get_entries_of_topic(entry),
            )
            if entry.mode in [TopicItemMode.indented, TopicItemMode.multilevel]
            else NavItemTopicEntry(
                id=entry.id,
                title=entry.title,
                mode=TopicItemMode.item,
                url=entry.url,
                target=entry.target,
                is_show_more=entry.is_show_more,
                icon=None if not user.get_attribute("icons_per_item") else entry.icon,
                toggle=entry.toggle if entry.toggle else None,
                chip=entry.chip if entry.chip else None,
                sort_index=entry.sort_index,
                entries=None,
            )
            for entry in sorted(topic.entries, key=lambda g: g.sort_index)
        ]

    def _add_unified_searchprovider(self, menu: MainMenuItem | MainMenuLinkItem) -> None:
        match menu.id:
            case ProviderName.monitoring | ProviderName.customize | ProviderName.setup:
                providers = dataclasses.replace(
                    self.search_config.providers,
                    **{menu.id.value: Provider(active=True, sort=menu.sort_index)},
                )
                self.search_config = dataclasses.replace(self.search_config, providers=providers)
            case _:
                pass


def ajax_message_read(ctx: PageContext) -> None:
    response.set_content_type("application/json")
    try:
        message.delete_gui_message(request.get_str_input_mandatory("id"))
        html.write_text_permissive("OK")
    except Exception:
        if ctx.config.debug:
            raise
        html.write_text_permissive("ERROR")


class PageAjaxSidebarChangesMenu(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        return {
            "number_of_pending_changes": ActivateChanges.get_number_of_pending_changes(
                sites=list(activation_sites(ctx.config.sites)),
                count_limit=10,
            )
        }


class PageAjaxSitesAndChanges(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        """Return all data required to render the "Quick activation of changes" slideout.

        Accepts an optional ``activation_id`` query parameter (UUID). When present, the
        live temporary activation state files are consulted first to reflect an in-progress
        activation. If those files are absent or incomplete, or the parameter is omitted,
        falls back to the persisted state of the last completed activation.

        Returns:
            A dict (serialized :class:`~cmk.shared_typing.changes.SitesAndChanges`)
            containing per-site status, the list of pending changes, and any
            licensing information.

        Raises:
            MKUserError: If ``activation_id`` is present but not a valid UUID string.
        """
        # validate_uuid_str rejects non-UUID strings; the value is used to
        # construct file paths so validation guards against path traversal.
        raw_activation_id = ctx.request.get_ascii_input("activation_id")
        if raw_activation_id is None:
            activation_id = None
        elif validate_uuid_str(raw_activation_id) is None:
            raise MKUserError("activation_id", _("Invalid activation_id"))
        else:
            activation_id = raw_activation_id
        return dataclasses.asdict(
            ActivateChanges().get_all_data_required_for_activation_popout(
                ctx.config.sites, activation_id
            )
        )


class PopUpMessage(TypedDict):
    id: str
    text: str


class PageAjaxSidebarGetMessages(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
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
    @override
    def page(self, ctx: PageContext) -> PageResult:
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
