#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The user profile mega menu and related AJAX endpoints"""

import cmk.utils.version as cmk_version

if cmk_version.edition() is cmk_version.Edition.CSE:
    from cmk.gui.cse.utils.roles import user_may_see_saas_onboarding

from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pages import AjaxPage, PageRegistry, PageResult
from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic
from cmk.gui.userdb import remove_custom_attr, validate_start_url
from cmk.gui.userdb.store import load_custom_attr, save_custom_attr
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.theme import theme, theme_choices
from cmk.gui.utils.urls import makeuri_contextless


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("ajax_ui_theme")(ModeAjaxCycleThemes)
    page_registry.register_page("ajax_sidebar_position")(ModeAjaxCycleSidebarPosition)
    page_registry.register_page("ajax_set_dashboard_start_url")(ModeAjaxSetStartURL)

    if cmk_version.edition() == cmk_version.Edition.CSE:
        page_registry.register_page("ajax_saas_onboarding_button_toggle")(
            ModeAjaxCycleSaasOnboardingButtonToggle
        )


def _get_current_theme_title() -> str:
    return [title for theme_id, title in theme.theme_choices if theme_id == theme.get()][0]


def _get_sidebar_position() -> str:
    assert user.id is not None
    sidebar_position = load_custom_attr(
        user_id=user.id,
        key="ui_sidebar_position",
        parser=lambda x: None if x == "None" else "left",
    )

    return sidebar_position or "right"


def _get_saas_onboarding_visibility_status() -> str | None:
    assert user.id is not None
    saas_onboarding_button_toggle = load_custom_attr(
        user_id=user.id,
        key="ui_saas_onboarding_button_toggle",
        parser=lambda x: None if x == "None" else x,
    )

    return saas_onboarding_button_toggle


def _sidebar_position_title(stored_value: str) -> str:
    return _("Left") if stored_value == "left" else _("Right")


def _sidebar_position_id(stored_value: str) -> str:
    return "left" if stored_value == "left" else "right"


def _user_menu_topics() -> list[TopicMenuTopic]:
    quick_items = [
        TopicMenuItem(
            name="ui_theme",
            title=_("Color theme"),
            url='javascript:cmk.sidebar.toggle_user_attribute("ajax_ui_theme.py")',
            target="",
            sort_index=10,
            icon="color_mode",
            button_title=_get_current_theme_title(),
        ),
        TopicMenuItem(
            name="sidebar_position",
            title=_("Sidebar position"),
            url='javascript:cmk.sidebar.toggle_user_attribute("ajax_sidebar_position.py")',
            target="",
            sort_index=20,
            icon="sidebar_position",
            button_title=_sidebar_position_title(_get_sidebar_position()),
        ),
    ]

    if cmk_version.edition() == cmk_version.Edition.CSE and user_may_see_saas_onboarding(user.id):
        quick_items.append(
            TopicMenuItem(
                name="saas_onboarding_button_toggle",
                title=_("Toggle onboarding button"),
                url='javascript:cmk.sidebar.toggle_user_attribute("ajax_saas_onboarding_button_toggle.py")',
                target="",
                sort_index=30,
                icon="sidebar_position",
                button_title=(
                    _("Visible")
                    if _get_saas_onboarding_visibility_status() is None
                    else _("Invisible")
                ),
            ),
        )

    items = [
        TopicMenuItem(
            name="user_profile",
            title=_("Edit profile"),
            url="user_profile.py",
            sort_index=10,
            icon="topic_profile",
        ),
    ]

    if cmk_version.edition() != cmk_version.Edition.CSE:
        items.extend(
            [
                TopicMenuItem(
                    name="change_password",
                    title=_("Change password"),
                    url="user_change_pw.py",
                    sort_index=30,
                    icon="topic_change_password",
                ),
                TopicMenuItem(
                    name="two_factor",
                    title=_("Two-factor authentication"),
                    url="user_two_factor_overview.py",
                    sort_index=30,
                    icon="topic_two_factor",
                ),
            ]
        )

    items.append(
        TopicMenuItem(
            name="logout",
            title=_("Logout"),
            url="logout.py",
            sort_index=40,
            icon="sidebar_logout",
            target="_self",
        )
    )

    if user.may("general.edit_notifications"):
        items.insert(
            1,
            TopicMenuItem(
                name="notification_rules",
                title=_("Notification rules"),
                url="wato.py?mode=user_notifications_p",
                sort_index=20,
                icon="topic_events",
            ),
        )

    return [
        TopicMenuTopic(
            name="user",
            title=_("User interface"),
            icon="topic_user_interface",
            items=quick_items,
        ),
        TopicMenuTopic(
            name="user",
            title=_("User profile"),
            icon="topic_profile",
            items=items,
        ),
    ]


mega_menu_registry.register(
    MegaMenu(
        name="user",
        title=_l("User"),
        icon="main_user",
        sort_index=20,
        topics=_user_menu_topics,
        info_line=lambda: f"{user.id} ({'+'.join(user.role_ids)})",
    )
)


class ModeAjaxCycleThemes(AjaxPage):
    """AJAX handler for quick access option 'Interface theme" in user menu"""

    def page(self) -> PageResult:
        check_csrf_token()
        themes = [theme for theme, _title in theme_choices()]
        current_theme = theme.get()
        try:
            theme_index = themes.index(current_theme)
        except ValueError:
            raise MKUserError(None, _("Could not determine current theme."))

        if len(themes) == theme_index + 1:
            new_theme = themes[0]
        else:
            new_theme = themes[theme_index + 1]

        _set_user_attribute("ui_theme", new_theme)
        return {}


class ModeAjaxCycleSidebarPosition(AjaxPage):
    """AJAX handler for quick access option 'Sidebar position" in user menu"""

    def page(self) -> PageResult:
        check_csrf_token()
        _set_user_attribute(
            "ui_sidebar_position",
            None if _sidebar_position_id(_get_sidebar_position()) == "left" else "left",
        )
        return {}


class ModeAjaxCycleSaasOnboardingButtonToggle(AjaxPage):
    """AJAX handler for quick access option 'Toggle onboarding button" in user menu"""

    def page(self) -> PageResult:
        check_csrf_token()
        _set_user_attribute(
            "ui_saas_onboarding_button_toggle",
            (None if _get_saas_onboarding_visibility_status() == "invisible" else "invisible"),
        )
        return {}


class ModeAjaxSetStartURL(AjaxPage):
    """AJAX handler to set the start URL of a user to a dashboard"""

    def page(self) -> PageResult:
        try:
            check_csrf_token()
            name = request.get_str_input_mandatory("name")
            url = makeuri_contextless(request, [("name", name)], "dashboard.py")
            validate_start_url(url, "")
            _set_user_attribute("start_url", repr(url))
        except Exception:
            raise MKUserError(None, _("Failed to set start URL"))
        return {}


def _set_user_attribute(key: str, value: str | None) -> None:
    assert user.id is not None
    user_id = user.id

    if value is None:
        remove_custom_attr(user_id, key)
    else:
        save_custom_attr(user_id, key, value)
