#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import datetime

from cmk.gui import forms, login, userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import page_registry
from cmk.gui.plugins.userdb.htpasswd import hash_password
from cmk.gui.plugins.wato.utils.base_modes import redirect
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib.users import verify_password_policy

from .abstract_page import ABCUserProfilePage


@page_registry.register_page("user_change_pw")
class UserChangePasswordPage(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Change password")

    def __init__(self) -> None:
        super().__init__("general.change_password")

    def _action(self) -> None:
        assert user.id is not None

        users = userdb.load_users(lock=True)
        user_spec = users[user.id]

        cur_password = request.get_str_input_mandatory("cur_password")
        password = request.get_str_input_mandatory("password")
        password2 = request.get_str_input_mandatory("password2", "")

        # Force change pw mode
        if not cur_password:
            raise MKUserError("cur_password", _("You need to provide your current password."))

        if not password:
            raise MKUserError("password", _("You need to change your password."))

        if cur_password == password:
            raise MKUserError("password", _("The new password must differ from your current one."))

        if userdb.check_credentials(user.id, cur_password) is False:
            raise MKUserError("cur_password", _("Your old password is wrong."))

        if password2 and password != password2:
            raise MKUserError("password2", _("The both new passwords do not match."))

        verify_password_policy(password)
        user_spec["password"] = hash_password(password)
        user_spec["last_pw_change"] = int(time.time())

        # In case the user was enforced to change it's password, remove the flag
        try:
            del user_spec["enforce_pw_change"]
        except KeyError:
            pass

        # Increase serial to invalidate old authentication cookies
        if "serial" not in user_spec:
            user_spec["serial"] = 1
        else:
            user_spec["serial"] += 1

        userdb.save_users(users, datetime.now())

        flash(_("Successfully changed password."))

        # Set the new cookie to prevent logout for the current user
        login.update_auth_cookie(user.id)

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        origtarget = request.get_str_input_mandatory("_origtarget", "user_change_pw.py")
        if user.authorized_login_sites():
            raise redirect(
                makeuri_contextless(
                    request, [("back", origtarget)], filename="user_profile_replicate.py"
                )
            )
        raise redirect(origtarget)

    def _show_form(self) -> None:
        assert user.id is not None

        users = userdb.load_users()

        change_reason = request.get_ascii_input("reason")

        if change_reason == "expired":
            html.p(_("Your password is too old, you need to choose a new password."))
        elif change_reason == "enforced":
            html.p(_("You are required to change your password before proceeding."))

        user_spec = users.get(user.id)
        if user_spec is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        locked_attributes = userdb.locked_attributes(user_spec.get("connector"))
        if "password" in locked_attributes:
            raise MKUserError(
                "cur_password",
                _("You can not change your password, because it is " "managed by another system."),
            )

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")
        forms.header(self._page_title())

        forms.section(_("Current Password"))
        html.password_input("cur_password", autocomplete="new-password")

        forms.section(_("New Password"))
        html.password_input("password", autocomplete="new-password")

        forms.section(_("New Password Confirmation"))
        html.password_input("password2", autocomplete="new-password")

        forms.end()
        html.close_div()
        html.hidden_fields()
        html.end_form()
        html.footer()
