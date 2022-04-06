#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.globals import active_config, html, request, user_errors
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.pages import Page
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import requested_file_name
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

        if not user.may(permission):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not active_config.wato_enabled:
            raise MKAuthException(_("User profiles can not be edited (WATO is disabled)."))

    def _page_menu(self, breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Profile"), breadcrumb, form_name="profile", button_name="_save"
        )
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(requested_file_name(request)))
        return menu

    def _breadcrumb(self) -> Breadcrumb:
        return make_simple_page_breadcrumb(mega_menu_registry.menu_user(), self._page_title())

    def page(self) -> None:
        title = self._page_title()
        breadcrumb = self._breadcrumb()
        html.header(title, breadcrumb, self._page_menu(breadcrumb))

        if transactions.check_transaction():
            try:
                self._action()
            except MKUserError as e:
                user_errors.add(e)

        for message in get_flashed_messages():
            html.show_message(message)

        html.show_user_errors()

        self._show_form()
