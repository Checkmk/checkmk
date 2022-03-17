#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterator

from cmk.gui.globals import user
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_link, PageMenuDropdown, PageMenuEntry, PageMenuTopic
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled


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
    if page_name != "user_change_pw":
        yield PageMenuEntry(
            title=_("Change password"),
            icon_name="topic_change_password",
            item=make_simple_link("user_change_pw.py"),
            is_shortcut=show_shortcuts,
        )

    if page_name != "user_two_factor_overview" and user.may("general.manage_2fa"):
        yield PageMenuEntry(
            title=_("Edit two-factor authentication"),
            icon_name="topic_2fa",
            item=make_simple_link("user_two_factor_overview.py"),
            is_shortcut=show_shortcuts,
        )

    if page_name != "user_profile":
        yield PageMenuEntry(
            title=_("Edit profile"),
            icon_name="topic_profile",
            item=make_simple_link("user_profile.py"),
            is_shortcut=show_shortcuts,
        )

    if (
        page_name != "user_notifications_p"
        and rulebased_notifications_enabled()
        and user.may("general.edit_notifications")
    ):
        yield PageMenuEntry(
            title=_("Notification rules"),
            icon_name="topic_events",
            item=make_simple_link("wato.py?mode=user_notifications_p"),
            is_shortcut=show_shortcuts,
        )
