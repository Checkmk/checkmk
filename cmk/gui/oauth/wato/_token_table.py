#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared rendering and action helpers for the OAuth grant list pages.

Used by both the self-service page (cmk.gui.oauth.wato._user_tokens_page) and
the admin Setup mode (cmk.gui.oauth.wato._user_tokens_mode) -- the two render
the same grant table, one scoped to the caller's own grants.
"""

from collections.abc import Callable, Collection, Mapping

from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.oauth.resource_names import resource_display_name
from cmk.gui.oauth.store.client_store import ClientId, ClientRegistration, get_client_store
from cmk.gui.oauth.token.token_store import get_token_store, GrantRecord, TokenStore
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


def remove_grants_from_request(
    request: Request, revoke: Callable[[TokenStore, Collection[str]], int]
) -> None:
    """Handle the _delete/_bulk_revoke_tokens actions shared by both grant-list pages.

    Callers are expected to have already checked the CSRF token and the
    transaction, same as any other action handler.

    revoke decides whose grants may be removed: only the caller's own on the
    self-service page, anyone's in Setup.
    """
    if grant_id := request.get_ascii_input("_delete"):
        with get_token_store() as store:
            deleted = revoke(store, [grant_id])
        if deleted:
            flash(_("Removed the session."))
        return

    if request.var("_bulk_revoke_tokens"):
        with get_token_store() as store:
            deleted = revoke(store, selected_grant_ids(request))
        if deleted:
            flash(_("Removed %(n)d sessions.") % {"n": deleted})


def selected_grant_ids(request: Request) -> list[str]:
    """grant_id of every checked '_c_grant_<id>' checkbox in request."""
    return [
        varname.removeprefix("_c_grant_")
        for varname, _value in request.itervars(prefix="_c_grant_")
        if html.get_checkbox(varname)
    ]


def render_selection_checkbox_cell(table: Table, grant_id: str) -> None:
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
    html.checkbox(f"_c_grant_{grant_id}")


def render_grant_summary_cells(
    table: Table, grant: GrantRecord, clients: Mapping[ClientId, ClientRegistration]
) -> None:
    table.cell(_("Client"), client_display_name(grant.client_id, clients))
    table.cell(_("Scope"), format_scopes(grant.scope))
    table.cell(_("Target"), resource_display_name(grant.resource))
    table.cell(_("Session created"), render.date_and_time(grant.created_at.timestamp()))


def bulk_revoke_page_menu_topics(selection_key: str, message: str) -> list[PageMenuTopic]:
    return [
        PageMenuTopic(
            title=_("On selected sessions"),
            entries=[
                PageMenuEntry(
                    title=_("Remove sessions"),
                    icon_name=StaticIcon(IconNames.delete),
                    item=make_confirmed_form_submit_link(
                        form_name="bulk_revoke_form",
                        button_name="_bulk_revoke_tokens",
                        title=_("Remove selected sessions"),
                        message=message,
                    ),
                    is_shortcut=True,
                    is_suggested=True,
                ),
            ],
        ),
        make_checkbox_selection_topic(selection_key),
    ]
