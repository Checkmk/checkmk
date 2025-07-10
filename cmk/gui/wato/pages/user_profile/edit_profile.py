#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A user can edit some user profile attributes on this page"""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from cmk.gui import forms, userdb
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import FinalizeRequest, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _u, localize
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import get_user_attributes, get_user_attributes_by_topic, UserAttribute
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.language_cookie import set_language_cookie
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import ValueSpec
from cmk.gui.wato.pages.users import select_language
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user

from .page_menu import user_profile_page_menu
from .verify_requirements import verify_requirements


def _get_input(valuespec: ValueSpec, varprefix: str) -> Any:
    value = valuespec.from_html_vars(varprefix)
    valuespec.validate_value(value, varprefix)
    return value


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_profile", UserProfile))


class UserProfile(Page):
    def _page_title(self) -> str:
        return _("Edit profile")

    def _action(self, config: Config) -> None:
        assert user.id is not None

        users = userdb.load_users(lock=True)
        user_spec = users[user.id]

        language = request.get_ascii_input_mandatory("language")
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

        # Custom attributes
        if user.may("general.edit_user_attributes"):
            for name, attr in get_user_attributes():
                if not attr.user_editable():
                    continue

                perm_name = attr.permission()
                if perm_name and not user.may(perm_name):
                    continue

                vs = attr.valuespec()
                value = vs.from_html_vars("ua_" + name)
                vs.validate_value(value, "ua_" + name)
                user_spec[name] = value  # type: ignore[literal-required]

        userdb.save_users(users, datetime.now())

        flash(_("Successfully updated user profile."))

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        if get_enabled_remote_sites_for_logged_in_user(user, config.sites):
            back_url = "user_profile_replicate.py?back=user_profile.py"
        else:
            back_url = "user_profile.py"

        # Ensure theme changes are applied without additional user interaction
        html.reload_whole_page(back_url)
        html.footer()

        raise FinalizeRequest(code=200)

    def page(self, config: Config) -> None:
        verify_requirements("general.edit_profile", config.wato_enabled)
        title = self._page_title()
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), self._page_title())
        make_header(html, title, breadcrumb, user_profile_page_menu(breadcrumb))

        if transactions.check_transaction():
            try:
                self._action(config)
            except MKUserError as e:
                user_errors.add(e)

        for message in get_flashed_messages():
            html.show_message(message.msg)

        html.show_user_errors()

        self._show_form()

    def _show_form(self) -> None:
        assert user.id is not None

        users = userdb.load_users()

        user_spec: UserSpec | None = users.get(user.id)
        if user_spec is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        with html.form_context("profile", method="POST"):
            html.prevent_password_auto_completion()
            html.open_div(class_="wato")
            forms.header(_("Personal settings"))

            forms.section(_("Username"), simple=True)
            html.write_text_permissive(user_spec.get("user_id", user.id))

            forms.section(_("Full name"), simple=True)
            html.write_text_permissive(user_spec.get("alias", ""))

            select_language(user_spec)

            if user.may("general.edit_user_attributes"):
                custom_user_attr_topics = get_user_attributes_by_topic()
                _show_custom_user_attr(user_spec, custom_user_attr_topics.get("personal", []))
                forms.header(_("User interface settings"))
                _show_custom_user_attr(user_spec, custom_user_attr_topics.get("interface", []))

            forms.end()
            html.close_div()
            html.hidden_fields()
        html.footer()


def _show_custom_user_attr(
    user_spec: UserSpec, custom_attr: Iterable[tuple[str, UserAttribute]]
) -> None:
    for name, attr in custom_attr:
        if attr.user_editable():
            vs = attr.valuespec()
            title = vs.title()
            assert title is not None  # Hmmm...
            forms.section(_u(title))
            value = user_spec.get(name, vs.default_value())
            permission = attr.permission()
            if not permission or user.may(permission):
                vs.render_input("ua_" + name, value)
                h = vs.help()
                if isinstance(h, str):
                    h = _u(h)
                html.help(h)
            else:
                html.write_text_permissive(vs.value_to_html(value))
