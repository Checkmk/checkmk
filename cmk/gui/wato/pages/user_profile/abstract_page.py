#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui import session
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
from cmk.gui.pages import Page
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related


class ABCUserProfilePage(Page):
    @abc.abstractmethod
    def _page_title(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _action(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_form(self) -> None:
        raise NotImplementedError()

    def __init__(self, permission: str) -> None:
        super().__init__()
        self._verify_requirements(permission)

    @staticmethod
    def _verify_requirements(permission: str) -> None:
        if not user.id:
            raise MKUserError(None, _("Not logged in."))

        # If the user is obligated to change his password, or 2FA is
        # enforced, he should be allowed to do so.
        if (
            request.get_ascii_input("reason") not in ("expired", "enforced")
            and not session.session.two_factor_enforced()
        ):
            if not user.may(permission):
                raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not active_config.wato_enabled:
            raise MKAuthException(_("User profiles can not be edited (Setup is disabled)."))

    def _page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Profile"), breadcrumb, form_name="profile", button_name="_save"
        )
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(requested_file_name(request)))
        return menu

    def _breadcrumb(self) -> Breadcrumb:
        return make_simple_page_breadcrumb(main_menu_registry.menu_user(), self._page_title())

    def page(self, config: Config) -> None:
        title = self._page_title()
        breadcrumb = self._breadcrumb()
        make_header(html, title, breadcrumb, self._page_menu(breadcrumb))

        if transactions.check_transaction():
            try:
                self._action()
            except MKUserError as e:
                user_errors.add(e)

        for message in get_flashed_messages():
            html.show_message(message.msg)

        html.show_user_errors()

        self._show_form()
