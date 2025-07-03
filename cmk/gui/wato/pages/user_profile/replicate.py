#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_profile_replicate", UserProfileReplicate))


class UserProfileReplicate(Page):
    def __init__(self) -> None:
        super().__init__()

        if not user.id:
            raise MKUserError(None, _("Not logged in."))

        if not user.may("general.change_password") and not user.may("general.edit_profile"):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not active_config.wato_enabled:
            raise MKAuthException(_("User profiles can not be edited (Setup is disabled)."))

    def _page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Profile"), breadcrumb, form_name="profile", button_name="_save"
        )
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(requested_file_name(request)))
        return menu

    def page(self, config: Config) -> None:
        title = _("Replicate user profile")
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), title)
        make_header(html, title, breadcrumb, self._page_menu(breadcrumb))

        # Now, if in distributed environment where users can login to remote sites, set the trigger for
        # pushing the new user profile to the remote sites asynchronously
        user_profile_async_replication_page(
            back_url=request.get_url_input("back", "user_profile.py")
        )
