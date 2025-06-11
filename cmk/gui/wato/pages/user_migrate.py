#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from collections.abc import Collection
from datetime import datetime

from cmk.ccc.user import UserId

from cmk.gui import userdb
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_simple_page_breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_confirmed_form_submit_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.type_defs import ActionResult, PermissionName, Users
from cmk.gui.userdb import connections_by_type, ConnectorType, get_connection, get_user_attributes
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import CascadingDropdown, Dictionary, ListChoice
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeUserMigrate)


class ModeUserMigrate(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "user_migrate"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["user_migrate"]

    def title(self) -> str:
        return _("Migrate users to another connection")

    def breadcrumb(self) -> Breadcrumb:
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_setup(), self.title())
        breadcrumb.insert(
            -1,
            BreadcrumbItem(
                title=_("Users"),
                url="wato.py?mode=users",
            ),
        )
        return breadcrumb

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="users",
                    title=_("Users"),
                    topics=[
                        PageMenuTopic(
                            title=_("Migrate"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Migrate users"),
                                    shortcut_title=_("Migrate selected users"),
                                    icon_name="migrate",
                                    item=make_confirmed_form_submit_link(
                                        form_name="user_migrate",
                                        button_name="_migrate",
                                        title=_("Migrate selected users"),
                                        message=_(
                                            "<b>Note</b>: If you migrate to <i>htpasswd</i> "
                                            "connector, the users will have to change "
                                            "their password on the next login."
                                        ),
                                        confirm_button=_("Migrate"),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    is_enabled=request.has_var("selection"),
                                )
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Users"),
                                    icon_name="users",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [
                                                ("mode", "users"),
                                            ],
                                            filename="wato.py",
                                        )
                                    ),
                                )
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

        return menu

    def page(self) -> None:
        if request.var("selection"):
            self._show_form_page()
        else:
            self._show_result_page()

    def _show_form_page(self) -> None:
        if not (selected_users := _get_selected_users()):
            raise MKUserError("users", _("You have to select at least one user."))

        html.show_message(
            _("You have selected %d %s for migration: %s")
            % (
                len(selected_users),
                ungettext("user", "users", len(selected_users)),
                _format_users(selected_users),
            )
        )

        with html.form_context("user_migrate", method="POST"):
            self._valuespec().render_input_as_form("_user_migrate", {})

            html.hidden_fields()
        html.footer()

    def _show_result_page(self) -> None:
        html.buttonlink(
            makeuri_contextless(
                request,
                [
                    ("mode", "users"),
                ],
                filename="wato.py",
            ),
            _("Back to users page"),
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        vs_user_migrate = self._valuespec()
        migration_params = self._valuespec().from_html_vars("_user_migrate")
        vs_user_migrate.validate_value(migration_params, "_user_migrate")
        if not (connector := migration_params.get("connector")):
            raise MKUserError("_user_migrate", _("You have to specify a connector to migrate to."))

        attributes: list[str] = migration_params.get("attributes", [])
        users_with_warning, users_migrated = self._migrate_users(connector, attributes)

        flashed_msg: str = _("Migrated %d %s to connector '%s': %s") % (
            len(users_migrated),
            ungettext("user", "users", len(users_migrated)),
            connector,
            _format_users(users_migrated),
        )

        connection = get_connection(connector)
        if connection is not None and (connection_type := connection.type()) in [
            ConnectorType.SAML2,
            ConnectorType.LDAP,
        ]:
            flashed_msg += "<br>" + _(
                "Please note: Connector specific user attributes may be set on the next %s."
            ) % (_("login") if connection_type == ConnectorType.SAML2 else _("synchronization"))

        if users_with_warning:
            flashed_msg += "<br><br>" + _("The following %s could not be found: %s") % (
                ungettext("user", "users", len(users_with_warning)),
                _format_users(users_with_warning),
            )

        flash(flashed_msg, "warning" if users_with_warning else "message")

        return redirect(mode_url("user_migrate", connector=connector))

    def _valuespec(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "connector",
                    CascadingDropdown(
                        title=_("Choose target user connector"),
                        help=_("Choose the connector, the user(s) should be migrated to."),
                        choices=_get_connector_choices(),
                    ),
                ),
                (
                    "attributes",
                    ListChoice(
                        title=_("Unset user attributes on migration"),
                        choices=_get_attribute_choices(),
                    ),
                ),
            ],
            optional_keys=["attributes"],
        )

    def _migrate_users(
        self,
        connector: str,
        attributes: list[str],
    ) -> tuple[list[str], list[str]]:
        users_with_warning: list[str] = []
        users_migrated: list[str] = []
        all_users: Users = userdb.load_users()
        for username in _get_selected_users():
            user_id = UserId(username)
            if username not in all_users:
                users_with_warning.append(username)
                continue

            for attribute in attributes:
                if attribute not in all_users[user_id]:
                    continue

                match attribute:
                    case "roles":
                        all_users[user_id]["roles"] = []
                    case _:
                        # TODO Expected TypedDict key to be string literal [misc]
                        all_users[user_id].pop(attribute, None)  # type: ignore[misc]

            all_users[user_id]["connector"] = connector
            if connector == "htpasswd":
                all_users[user_id]["enforce_pw_change"] = True

            users_migrated.append(username)

        userdb.save_users(all_users, datetime.now())

        return users_with_warning, users_migrated


def _get_attribute_choices() -> list[tuple[str, str]]:
    # TODO can we collect all together somehow?
    default_choices: list[tuple[str, str]] = [
        ("email", "Email address"),
        ("pager", "Pager address"),
        ("contactgroups", "Contact groups"),
        ("fallback_contact", "Receive fallback notifications"),
        ("roles", "Roles"),
    ]

    builtin_attribute_choices: list[tuple[str, str]] = []
    for name, attr in get_user_attributes():
        builtin_attribute_choices.append((name, attr.valuespec().title() or attr.name()))

    return default_choices + builtin_attribute_choices


def _get_selected_users() -> list[str]:
    selected_users: list[str] = []
    for selection in user.get_rowselection(
        SelectionId.from_request(request),
        "users",
    ):
        selected_users.append(
            base64.b64decode(selection.split("_c_user_")[-1].encode("utf-8")).decode("utf-8")
        )
    return sorted(selected_users)


def _get_connector_choices() -> list[tuple[str, str, None]]:
    connector_choices = [("htpasswd", "Local user (htpasswd)", None)]

    for connector_type in [ConnectorType.LDAP, ConnectorType.SAML2]:
        connector_choices += [
            (connection["id"], f"{connector_type.upper()}: {connection['id']}", None)
            for connection in connections_by_type(connector_type)
        ]
    return connector_choices


def _format_users(users: list[str]) -> str:
    return ", ".join([f"<b>{user}</b>" for user in users])
