#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A user can edit some user profile attributes on this page"""

from datetime import datetime
from typing import Any, Optional

from cmk.gui import forms, userdb
from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.htmllib.context import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _u, localize
from cmk.gui.logged_in import user
from cmk.gui.pages import page_registry
from cmk.gui.plugins.userdb.utils import get_user_attributes_by_topic
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.language_cookie import set_language_cookie
from cmk.gui.valuespec import ValueSpec
from cmk.gui.wato.pages.users import select_language
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.watolib.users import get_vs_flexible_notifications

from .abstract_page import ABCUserProfilePage


def _get_input(valuespec: ValueSpec, varprefix: str) -> Any:
    value = valuespec.from_html_vars(varprefix)
    valuespec.validate_value(value, varprefix)
    return value


@page_registry.register_page("user_profile")
class UserProfile(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Edit profile")

    def __init__(self) -> None:
        super().__init__("general.edit_profile")

    def _action(self) -> None:
        assert user.id is not None

        users = userdb.load_users(lock=True)
        user_spec = users[user.id]

        language = request.get_ascii_input_mandatory("language", "")
        # Set the users language if requested to set it explicitly
        if language != "_default_":
            user_spec["language"] = language
            user.language = language
            set_language_cookie(request, response, language)

        else:
            if "language" in user_spec:
                del user_spec["language"]
            user.reset_language()

        # load the new language
        localize(user.language)

        if user.may("general.edit_notifications") and user_spec.get("notifications_enabled"):
            value = _get_input(get_vs_flexible_notifications(), "notification_method")
            user_spec["notification_method"] = value

        # Custom attributes
        if user.may("general.edit_user_attributes"):
            for name, attr in userdb.get_user_attributes():
                if not attr.user_editable():
                    continue

                perm_name = attr.permission()
                if perm_name and not user.may(perm_name):
                    continue

                vs = attr.valuespec()
                value = vs.from_html_vars("ua_" + name)
                vs.validate_value(value, "ua_" + name)
                # TODO: Dynamically fiddling around with a TypedDict is a bit questionable
                user_spec[name] = value  # type: ignore[literal-required]

        userdb.save_users(users, datetime.now())

        flash(_("Successfully updated user profile."))

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        if user.authorized_login_sites():
            back_url = "user_profile_replicate.py?back=user_profile.py"
        else:
            back_url = "user_profile.py"

        # Ensure theme changes are applied without additional user interaction
        html.reload_whole_page(back_url)
        html.footer()

        raise FinalizeRequest(code=200)

    def _show_form(self) -> None:
        assert user.id is not None

        users = userdb.load_users()

        user_spec: Optional[UserSpec] = users.get(user.id)
        if user_spec is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")
        forms.header(_("Personal settings"))

        forms.section(_("Username"), simple=True)
        html.write_text(user_spec.get("user_id", user.id))

        forms.section(_("Full name"), simple=True)
        html.write_text(user_spec.get("alias", ""))

        select_language(user_spec)

        # Let the user configure how he wants to be notified
        rulebased_notifications = rulebased_notifications_enabled()
        if (
            not rulebased_notifications
            and user.may("general.edit_notifications")
            and user_spec.get("notifications_enabled")
        ):
            forms.section(_("Notifications"))
            html.help(
                _(
                    "Here you can configure how you want to be notified about host and service problems and "
                    "other monitoring events."
                )
            )
            get_vs_flexible_notifications().render_input(
                "notification_method", user_spec.get("notification_method")
            )

        if user.may("general.edit_user_attributes"):
            custom_user_attr_topics = get_user_attributes_by_topic()
            _show_custom_user_attr(user_spec, custom_user_attr_topics.get("personal", []))
            forms.header(_("User interface settings"))
            _show_custom_user_attr(user_spec, custom_user_attr_topics.get("interface", []))

        forms.end()
        html.close_div()
        html.hidden_fields()
        html.end_form()
        html.footer()


def _show_custom_user_attr(user_spec: UserSpec, custom_attr) -> None:
    for name, attr in custom_attr:
        if attr.user_editable():
            vs = attr.valuespec()
            forms.section(_u(vs.title()))
            value = user_spec.get(name, vs.default_value())
            if not attr.permission() or user.may(attr.permission()):
                vs.render_input("ua_" + name, value)
                html.help(_u(vs.help()))
            else:
                html.write_text(vs.value_to_html(value))
