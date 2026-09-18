#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared rendering and action helpers for the OAuth access-token list pages.

Used by both the self-service page (cmk.gui.oauth.wato._user_tokens_page) and
the admin Setup mode (cmk.gui.oauth.wato._user_tokens_mode) -- the two render
the same token table, one scoped to the caller's own tokens.
"""

from collections.abc import Mapping

from cmk.ccc.user import UserId
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.oauth.resource_names import resource_display_name
from cmk.gui.oauth.store.client_store import ClientId, ClientRegistration, get_client_store
from cmk.gui.oauth.token.token_store import get_token_store, TokenRecord
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_confirmed_form_submit_link,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.scopes import format_scopes
from cmk.gui.table import Table
from cmk.utils import render
from cmk.web.utils.flashed_messages import flash
from cmk.web.utils.icons import IconNames, StaticIcon


def load_clients_by_id() -> dict[ClientId, ClientRegistration]:
    with get_client_store() as store:
        return {client.client_id: client for client in store.list()}


def client_display_name(client_id: str, clients: Mapping[ClientId, ClientRegistration]) -> str:
    client = clients.get(ClientId(client_id))
    return client.client_name if client and client.client_name else client_id


def revoke_tokens_from_request(request: Request, *, user_id: UserId | None) -> None:
    """Handle the _delete/_bulk_revoke_tokens actions shared by both token-list pages.

    Callers are expected to have already checked the CSRF token and the
    transaction, same as any other action handler.

    user_id scopes the revocation to that user's own tokens (self-service page);
    None revokes regardless of owner (admin mode).
    """
    if token_hash := request.get_ascii_input("_delete"):
        with get_token_store() as store:
            deleted = store.revoke([token_hash], user_id=user_id)
        if deleted:
            flash(_("Revoked the access token."))
        return

    if request.var("_bulk_revoke_tokens"):
        with get_token_store() as store:
            deleted = store.revoke(selected_token_hashes(request), user_id=user_id)
        if deleted:
            flash(_("Revoked %(n)d access tokens.") % {"n": deleted})


def selected_token_hashes(request: Request) -> list[str]:
    """token_hash of every checked '_c_token_<hash>' checkbox in request."""
    return [
        varname.removeprefix("_c_token_")
        for varname, _value in request.itervars(prefix="_c_token_")
        if html.get_checkbox(varname)
    ]


def render_selection_checkbox_cell(table: Table, token_hash: str) -> None:
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
    html.checkbox(f"_c_token_{token_hash}")


def render_token_summary_cells(
    table: Table, token: TokenRecord, clients: Mapping[ClientId, ClientRegistration]
) -> None:
    table.cell(_("Client"), client_display_name(token.client_id, clients))
    table.cell(_("Scope"), format_scopes(token.scope))
    table.cell(_("Target"), resource_display_name(token.resource))
    table.cell(_("Issued"), render.date_and_time(token.issued_at.timestamp()))
    table.cell(_("Expires"), render.date_and_time(token.expires_at.timestamp()))


def bulk_revoke_page_menu_topics(selection_key: str, message: str) -> list[PageMenuTopic]:
    return [
        PageMenuTopic(
            title=_("On selected tokens"),
            entries=[
                PageMenuEntry(
                    title=_("Revoke tokens"),
                    icon_name=StaticIcon(IconNames.delete),
                    item=make_confirmed_form_submit_link(
                        form_name="bulk_revoke_form",
                        button_name="_bulk_revoke_tokens",
                        title=_("Revoke selected access tokens"),
                        message=message,
                    ),
                    is_shortcut=True,
                    is_suggested=True,
                ),
            ],
        ),
        make_checkbox_selection_topic(selection_key),
    ]
