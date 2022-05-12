#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.pages import Page, page_registry
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.wato.pages.user_profile.async_replication import user_profile_async_replication_page
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related


@page_registry.register_page("user_profile_replicate")
class UserProfileReplicate(Page):
    def __init__(self) -> None:
        super().__init__()

        if not user.id:
            raise MKUserError(None, _("Not logged in."))

        if not user.may("general.change_password") and not user.may("general.edit_profile"):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not active_config.wato_enabled:
            raise MKAuthException(_("User profiles can not be edited (WATO is disabled)."))

    def _page_menu(self, breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Profile"), breadcrumb, form_name="profile", button_name="_save"
        )
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(requested_file_name(request)))
        return menu

    def page(self) -> None:
        title = _("Replicate user profile")
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_user(), title)
        make_header(html, title, breadcrumb, self._page_menu(breadcrumb))

        for message in get_flashed_messages():
            html.show_message(message)

        # Now, if in distributed environment where users can login to remote sites, set the trigger for
        # pushing the new user profile to the remote sites asynchronously
        user_profile_async_replication_page(
            back_url=request.get_url_input("back", "user_profile.py")
        )
