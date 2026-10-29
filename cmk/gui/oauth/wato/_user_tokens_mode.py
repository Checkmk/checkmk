#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.oauth.token.token_store import get_token_store, TokenStore
from cmk.gui.oauth.wato._token_table import (
    bulk_revoke_page_menu_topics,
    load_clients_by_id,
    remove_grants_from_request,
    render_grant_summary_cells,
    render_selection_checkbox_cell,
)
from cmk.gui.page_menu import PageMenu, PageMenuDropdown
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeOAuthTokens)


class ModeOAuthTokens(WatoMode[object]):
    @classmethod
    @override
    def name(cls) -> str:
        return "oauth_tokens"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @override
    def title(self) -> str:
        return _("OAuth sessions")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        topics = bulk_revoke_page_menu_topics(
            self.name(),
            _(
                "The applications using the selected sessions will no longer be"
                " able to access the API."
            ),
        )
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name=self.name(),
                    title=_("Sessions"),
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
        remove_grants_from_request(request, TokenStore.revoke_any_grants)
        return redirect(self.mode_url())

    @override
    def page(self, config: Config) -> None:
        # Read before emitting any HTML, so an unusable store shows as an error
        # message instead of a half-rendered table.
        with get_token_store() as store:
            grants = store.list_all_usable_grants()
        clients = load_clients_by_id()

        with html.form_context("bulk_revoke_form", method="POST"):
            with table_element("oauth_user_tokens", limit=config.table_row_limit) as table:
                for grant in grants:
                    table.row()
                    render_selection_checkbox_cell(table, grant.grant_id)

                    table.cell(_("Actions"), css=["buttons"])
                    delete_url = make_confirm_delete_link(
                        url=make_action_link([("mode", self.name()), ("_delete", grant.grant_id)]),
                        title=_("Remove session"),
                        suffix=grant.user_id,
                        message=_(
                            "The application using this session will no longer be able to"
                            " access the API."
                        ),
                    )
                    html.icon_button(
                        delete_url, _("Remove this session"), StaticIcon(IconNames.delete)
                    )

                    table.cell(_("User"), grant.user_id)
                    render_grant_summary_cells(table, grant, clients)
            html.hidden_fields()
