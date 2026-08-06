#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Collection
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.oauth import client_store
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_confirmed_form_submit_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.utils import render


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRegisteredOAuthClients)


class ModeRegisteredOAuthClients(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "oauth_registered_clients"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @override
    def title(self) -> str:
        return _("Registered OAuth clients")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        topics = [
            PageMenuTopic(
                title=_("On selected clients"),
                entries=[
                    PageMenuEntry(
                        title=_("Delete clients"),
                        icon_name=StaticIcon(IconNames.delete),
                        item=make_confirmed_form_submit_link(
                            form_name="bulk_delete_form",
                            button_name="_bulk_delete_clients",
                            title=_("Delete selected clients"),
                            message=_(
                                "All access tokens issued to the selected clients"
                                " are revoked immediately."
                            ),
                        ),
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                ],
            ),
            make_checkbox_selection_topic(self.name()),
        ]
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name=self.name(),
                    title=_("Clients"),
                    topics=topics,
                ),
            ],
            breadcrumb=breadcrumb,
        )

    @override
    def action(self, config: Config) -> ActionResult:
        check_csrf_token()
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if delete_client := request.get_ascii_input("_delete"):
            deleted = client_store().delete([delete_client])
            if deleted:
                flash(_("Deleted the client."))
            return redirect(self.mode_url())

        if request.var("_bulk_delete_clients"):
            selected = [
                varname.removeprefix("_c_client_")
                for varname, _value in request.itervars(prefix="_c_client_")
                if html.get_checkbox(varname)
            ]
            deleted = client_store().delete(selected)
            if deleted:
                flash(_("Deleted %(n)d clients.") % {"n": deleted})
            return redirect(self.mode_url())

        return redirect(self.mode_url())

    @override
    def page(self, config: Config) -> None:
        with html.form_context("bulk_delete_form", method="POST"):
            with table_element("oauth_registered_clients", limit=config.table_row_limit) as table:
                for client in client_store().list():
                    table.row()
                    table.cell(
                        html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows(this.form);",
                            value="X",
                        ),
                        sortable=False,
                        css=["checkbox"],
                    )
                    html.checkbox(f"_c_client_{client.client_id}")

                    table.cell(_("Actions"), css=["buttons"])
                    delete_url = make_confirm_delete_link(
                        url=make_action_link(
                            request, [("mode", self.name()), ("_delete", client.client_id)]
                        ),
                        title=_("Delete registered client"),
                        suffix=client.client_name or client.client_id,
                        message=_(
                            "All access tokens issued to this client are revoked immediately."
                        ),
                    )
                    html.icon_button(
                        delete_url, _("Delete this client"), StaticIcon(IconNames.delete)
                    )

                    table.cell(_("Client ID"), client.client_id)
                    table.cell(_("Client name"), client.client_name or "")
                    table.cell(_("Redirect URIs"), ", ".join(client.redirect_uris))
                    table.cell(
                        _("Registered"), render.date_and_time(client.registered_at.timestamp())
                    )
            html.hidden_fields()
