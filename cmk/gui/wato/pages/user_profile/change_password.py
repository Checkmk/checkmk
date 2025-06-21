#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import datetime

from cmk.utils.log.security_event import log_security_event

from cmk.gui import forms, userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.session import session
from cmk.gui.userdb._connections import get_connection
from cmk.gui.userdb.htpasswd import hash_password
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.security_log_events import UserManagementEvent
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_security_message import SecurityNotificationEvent, send_security_message
from cmk.gui.watolib.mode import redirect
from cmk.gui.watolib.users import (
    get_enabled_remote_sites_for_logged_in_user,
    verify_password_policy,
)

from cmk.crypto.password import Password

from .abstract_page import ABCUserProfilePage


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_change_pw", UserChangePasswordPage))


class UserChangePasswordPage(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Change password")

    def __init__(self) -> None:
        super().__init__("general.change_password")

    def _action(self) -> None:
        assert user.id is not None

        users = userdb.load_users(lock=True)
        user_spec = users[user.id]

        cur_password = request.get_validated_type_input(
            Password, "cur_password", empty_is_none=True
        )
        password = request.get_validated_type_input(Password, "password", empty_is_none=True)
        password2 = request.get_validated_type_input(Password, "password2", empty_is_none=True)

        # Force change pw mode
        if not cur_password:
            raise MKUserError("cur_password", _("You need to provide your current password."))

        if not password:
            raise MKUserError("password", _("You need to change your password."))

        if cur_password == password:
            raise MKUserError("password", _("The new password must differ from your current one."))

        now = datetime.now()
        if userdb.check_credentials(user.id, cur_password, now) is False:
            raise MKUserError("cur_password", _("Your old password is wrong."))

        if password2 and password != password2:
            raise MKUserError("password2", _("New passwords don't match."))

        verify_password_policy(password)
        user_spec["password"] = hash_password(password)
        user_spec["last_pw_change"] = int(time.time())
        send_security_message(user.id, SecurityNotificationEvent.password_change)

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

        userdb.save_users(users, now)
        connection_id = user_spec.get("connector", None)
        connection = get_connection(connection_id)
        log_security_event(
            UserManagementEvent(
                event="password changed",
                affected_user=user.id,
                acting_user=user.id,
                connector=connection.type() if connection else None,
                connection_id=connection_id,
            )
        )

        flash(_("Successfully changed password."))

        # Set the new cookie to prevent logout for the current user
        session.update_cookie()

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        origtarget = request.get_str_input_mandatory("_origtarget", "user_change_pw.py")
        if get_enabled_remote_sites_for_logged_in_user(user):
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
                _("You can not change your password, because it is managed by another system."),
            )

        with html.form_context("profile", method="POST"):
            html.prevent_password_auto_completion()
            html.open_div(class_="wato")
            forms.header(self._page_title())

            forms.section(_("Current password"))
            html.password_input("cur_password", autocomplete="new-password")

            forms.section(_("New password"))
            html.password_input("password", autocomplete="new-password")
            html.password_meter()

            forms.section(_("New password confirmation"))
            html.password_input("password2", autocomplete="new-password")

            html.hidden_field("_origtarget", request.get_str_input("_origtarget"))

            forms.end()
            html.close_div()
            html.hidden_fields()
        html.footer()
