#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The user profile main menu and related AJAX endpoints"""

from collections.abc import Callable
from typing import override

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import MainMenuItem
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.theme.choices import theme_choices
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import HTTPVariables, IconNames
from cmk.gui.userdb import remove_custom_attr, validate_start_url
from cmk.gui.userdb.store import load_custom_attr, save_custom_attr
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.shared_typing.main_menu import (
    ChipModeEnum,
    ColorEnum,
    DefaultIcon,
    NavItemHeader,
    NavItemIdEnum,
    NavItemShortcut,
    NavItemTopic,
    NavItemTopicEntry,
    NavItemTopicEntryChip,
    NavItemTopicEntryToggle,
)


def register(
    page_registry: PageRegistry,
    main_menu_registry: MainMenuRegistry,
    user_menu_topics: Callable[[UserPermissions], list[NavItemTopic]],
) -> None:
    page_registry.register(PageEndpoint("ajax_ui_theme", ModeAjaxCycleThemes()))
    page_registry.register(PageEndpoint("ajax_sidebar_position", ModeAjaxCycleSidebarPosition()))
    page_registry.register(PageEndpoint("ajax_set_dashboard_start_url", ModeAjaxSetStartURL()))
    page_registry.register(PageEndpoint("ajax_set_change_action", ModeAjaxChangesAction()))

    main_menu_registry.register(
        MainMenuItem(
            id=NavItemIdEnum.user,
            title=_l("User"),
            sort_index=20,
            get_topics=user_menu_topics,
            is_user_nav=True,
            shortcut=NavItemShortcut(key="u", alt=True),
            info_line=lambda: f"{user.id} ({'+'.join(user.role_ids)})",
            popup_small=True,
            header=NavItemHeader(),
            hint=_l("Manage personal settings"),
        )
    )


def _get_current_theme_title() -> str:
    return [title for theme_id, title in theme.theme_choices.items() if theme_id == theme.get()][0]


def _get_sidebar_position() -> str:
    assert user.id is not None
    sidebar_position = load_custom_attr(
        user_id=user.id,
        key="ui_sidebar_position",
        parser=lambda x: None if x == "None" else "left",
    )

    return sidebar_position or "right"


def _sidebar_position_title(stored_value: str) -> str:
    return _("Left") if stored_value == "left" else _("Right")


def _sidebar_position_id(stored_value: str) -> str:
    return "left" if stored_value == "left" else "right"


def default_user_menu_topics(
    user_permissions: UserPermissions,
    add_change_password_menu_item: bool = True,
    add_two_factor_menu_item: bool = True,
) -> list[NavItemTopic]:
    quick_entries: list[NavItemTopicEntry] = [
        NavItemTopicEntry(
            id="ui_theme",
            title=_("Color theme"),
            url=None,
            target=None,
            icon=DefaultIcon(id=IconNames.color_mode),
            toggle=NavItemTopicEntryToggle(
                mode="ajax_ui_theme.py",
                value=_get_current_theme_title(),
                color=ColorEnum.success,
                reload=True,
            ),
            sort_index=10,
        ),
        NavItemTopicEntry(
            id="sidebar_position",
            title=_("Sidebar position"),
            url=None,
            target=None,
            icon=DefaultIcon(id=IconNames.sidebar_position),
            toggle=NavItemTopicEntryToggle(
                mode="ajax_sidebar_position.py",
                value=_sidebar_position_title(_get_sidebar_position()),
                color=ColorEnum.success,
                reload=True,
            ),
            sort_index=20,
        ),
    ]

    entries: list[NavItemTopicEntry] = (
        [
            NavItemTopicEntry(
                id="user_profile",
                title=_("Edit profile"),
                url="user_profile.py",
                sort_index=10,
                icon=DefaultIcon(id=IconNames.topic_profile),
            ),
        ]
        if user.may("general.edit_profile")
        else []
    )

    if user.may("general.change_password") and add_change_password_menu_item:
        entries.append(
            NavItemTopicEntry(
                id="change_password",
                title=_("Change password"),
                url="user_change_pw.py",
                icon=DefaultIcon(id=IconNames.topic_change_password),
                sort_index=20,
            )
        )

    if user.may("general.manage_2fa") and add_two_factor_menu_item:
        entries.append(
            NavItemTopicEntry(
                id="two_factor",
                title=_("Two-factor authentication"),
                url="user_two_factor_overview.py",
                icon=DefaultIcon(id=IconNames.topic_2fa),
                sort_index=30,
            ),
        )

    entries.append(
        NavItemTopicEntry(
            id="logout",
            title=_("Logout"),
            url="logout.py",
            icon=DefaultIcon(id=IconNames.sidebar_logout),
            target="_self",
            sort_index=40,
        )
    )

    if user.may("general.edit_notifications"):
        entries.append(
            NavItemTopicEntry(
                id="notification_rules",
                title=_("Notification rules"),
                url="wato.py?mode=user_notifications_p",
                icon=DefaultIcon(id=IconNames.topic_events),
                sort_index=5,
            ),
        )

    return [
        NavItemTopic(
            id="user_interface",
            title=_("User interface"),
            icon=DefaultIcon(id=IconNames.topic_user_interface),
            entries=quick_entries,
            sort_index=10,
        ),
        NavItemTopic(
            id="user_messages",
            title=_("User messages"),
            icon=DefaultIcon(id=IconNames.topic_events),
            entries=[
                NavItemTopicEntry(
                    id="user_messages",
                    title=_("Received messages"),
                    url="user_message.py",
                    icon=DefaultIcon(id=IconNames.topic_events),
                    chip=NavItemTopicEntryChip(
                        color=ColorEnum.danger, mode=ChipModeEnum.user_messages_hint
                    ),
                    sort_index=10,
                )
            ],
            sort_index=20,
        ),
        NavItemTopic(
            id="user_profile",
            title=_("User profile"),
            icon=DefaultIcon(id=IconNames.topic_profile),
            entries=entries,
            sort_index=30,
        ),
    ]


class ModeAjaxCycleThemes(AjaxPage):
    """AJAX handler for quick access option 'Interface theme" in user menu"""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        check_csrf_token(ctx.request.get_json()["_csrf_token"])
        themes = [theme for theme, _title in theme_choices()]
        # TODO: avoid global theme if possible
        current_theme = theme.get()
        try:
            theme_index = themes.index(current_theme)
        except ValueError:
            raise MKUserError(None, _("Could not determine current theme."))

        if len(themes) == theme_index + 1:
            new_theme = themes[0]
        else:
            new_theme = themes[theme_index + 1]

        set_user_attribute("ui_theme", new_theme)
        return {}


class ModeAjaxChangesAction(AjaxPage):
    """AJAX handler for setting the changes action preference in the changes menu"""

    _VALID_ACTIONS = frozenset({"full_page", "slideout"})

    @override
    def page(self, ctx: PageContext) -> PageResult:
        body = ctx.request.get_json()
        check_csrf_token(body["_csrf_token"])

        action = body.get("action")
        if action not in self._VALID_ACTIONS:
            raise MKUserError(None, _("Invalid action: %s") % action)

        set_user_attribute("navbar_changes_action", action)
        return {}


class ModeAjaxCycleSidebarPosition(AjaxPage):
    """AJAX handler for quick access option 'Sidebar position" in user menu"""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        check_csrf_token(ctx.request.get_json()["_csrf_token"])
        set_user_attribute(
            "ui_sidebar_position",
            None if _sidebar_position_id(_get_sidebar_position()) == "left" else "left",
        )
        return {}


class ModeAjaxSetStartURL(AjaxPage):
    """AJAX handler to set the start URL of a user"""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        try:
            check_csrf_token()
            if ctx.request.var("name"):
                name = ctx.request.get_str_input_mandatory("name")
                if name == "welcome.py":
                    set_user_attribute("start_url", repr(name))
                else:
                    variables: HTTPVariables = [("name", name)]
                    if (owner := ctx.request.get_str_input("owner")) is not None:
                        variables.append(("owner", owner))
                    url = makeuri_contextless(ctx.request, variables, "dashboard.py")
                    validate_start_url(url, "")
                    set_user_attribute("start_url", repr(url))
            else:
                set_user_attribute("start_url", None)
        except Exception as e:
            raise MKUserError(None, _("Failed to set start URL: %s") % e)
        return {}


def set_user_attribute(key: str, value: str | None) -> None:
    assert user.id is not None
    user_id = user.id

    if value is None:
        remove_custom_attr(user_id, key)
    else:
        save_custom_attr(user_id, key, value)
