#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import cmk.ccc.version as cmk_version
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.utils.urls import requested_file_name
from cmk.utils import paths


def user_profile_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = make_simple_form_page_menu(
        _("Profile"), breadcrumb, form_name="profile", button_name="_save"
    )
    menu.dropdowns.insert(1, page_menu_dropdown_user_related(requested_file_name(request)))
    return menu


def page_menu_dropdown_user_related(
    page_name: str, show_shortcuts: bool = True
) -> PageMenuDropdown:
    return PageMenuDropdown(
        name="related",
        title=_("Related"),
        topics=[
            PageMenuTopic(
                title=_("User"),
                entries=list(_page_menu_entries_related(page_name, show_shortcuts)),
            ),
        ],
    )


def _page_menu_entries_related(
    page_name: str, show_shortcuts: bool = True
) -> Iterator[PageMenuEntry]:
    is_cse_edition = cmk_version.edition(paths.omd_root) == cmk_version.Edition.CSE

    must_change_password = request.get_ascii_input("reason") in ("expired", "enforced")

    if page_name != "user_change_pw" and not is_cse_edition:
        yield PageMenuEntry(
            title=_("Change password"),
            icon_name="topic_change_password",
            item=make_simple_link("user_change_pw.py"),
            is_shortcut=show_shortcuts,
        )

    if (
        page_name != "user_two_factor_overview"
        and user.may("general.manage_2fa")
        and not is_cse_edition
        and not must_change_password
    ):
        yield PageMenuEntry(
            title=_("Edit two-factor authentication"),
            icon_name="topic_2fa",
            item=make_simple_link("user_two_factor_overview.py"),
            is_shortcut=show_shortcuts,
        )

    if (
        page_name != "user_profile"
        and user.may("general.edit_profile")
        and not must_change_password
    ):
        yield PageMenuEntry(
            title=_("Edit profile"),
            icon_name="topic_profile",
            item=make_simple_link("user_profile.py"),
            is_shortcut=show_shortcuts,
        )

    if (
        page_name != "user_notifications_p"
        and user.may("general.edit_notifications")
        and not must_change_password
    ):
        yield PageMenuEntry(
            title=_("Notification rules"),
            icon_name="topic_events",
            item=make_simple_link("wato.py?mode=user_notifications_p"),
            is_shortcut=show_shortcuts,
        )
