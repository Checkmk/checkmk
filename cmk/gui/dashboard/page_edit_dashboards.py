#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Callable

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.table import Table
from cmk.gui.token_auth import get_token_store, TokenId
from cmk.gui.type_defs import VisualName
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.visuals._store import TVisual

from .store import get_all_dashboards
from .type_defs import DashboardConfig, DashboardName

PAGE_EDIT_DASHBOARDS_LINK = "edit_dashboards"


def page_edit_dashboards(ctx: PageContext) -> None:
    visuals.page_list(
        what="dashboards",
        title=_("Edit dashboards"),
        visuals=get_all_dashboards(),
        user_permissions=UserPermissions.from_config(ctx.config, permission_registry),
        render_custom_buttons=_render_dashboard_buttons(ctx.request),
        render_custom_columns=_render_dashboard_columns(),
    )


def _render_dashboard_buttons(request: Request) -> Callable[[DashboardName, DashboardConfig], None]:
    def render(dashboard_name: DashboardName, dashboard: DashboardConfig) -> None:
        owner = dashboard["owner"]
        if owner == user.id or (
            owner != UserId.builtin() and user.may("general.edit_foreign_dashboards")
        ):
            if dashboard.get("show_title"):
                html.icon_button(
                    makeuri_contextless(
                        request,
                        [
                            ("owner", owner),
                            ("name", dashboard_name),
                            ("edit", "1"),
                        ],
                        "dashboard.py",
                    ),
                    title=_("Edit layout"),
                    icon="dashboard",
                )
            else:
                html.icon(
                    icon="dashboard",
                    title=_("Edit layout only available if header is enabled"),
                    cssclass="colorless",
                )

    return render


def _render_dashboard_columns() -> Callable[[Table, VisualName, TVisual], None]:
    # Read the token store once instead of for each table row
    with get_token_store().read_locked() as data:
        _tokens = data

    def _get_token_status_label(valid_until: dt.datetime | None, disabled: bool) -> str:
        """The human-readable status string for the dashboard share."""
        if disabled:
            return _("Disabled")

        if valid_until is None:
            return _("Shared")

        now = dt.datetime.now(dt.UTC)
        if valid_until > now:
            return _("Expires %s") % valid_until.strftime("%Y-%m-%d")

        return _("Expired %s") % valid_until.strftime("%Y-%m-%d")

    def _render_not_shared(table: Table) -> None:
        table.cell(_("Public link"), _("Not shared"))
        table.cell(_("Link created"), "")
        table.cell(_("Comments"), "")

    def render(table: Table, dashboard_name: VisualName, dashboard_config: TVisual) -> None:
        # do not add columns for built-in dashboards
        if dashboard_config.get("owner") == UserId.builtin():
            return

        if not (plain_token_id := dashboard_config.get("public_token_id")):
            _render_not_shared(table)
            return

        if not (auth_token := _tokens.get(TokenId(str(plain_token_id)))):
            _render_not_shared(table)
            return

        table.cell(
            _("Public link"),
            _get_token_status_label(auth_token.valid_until, auth_token.details.disabled),
        )
        table.cell(_("Link created"), auth_token.issued_at.strftime("%Y-%m-%d"))
        table.cell(_("Comments"), auth_token.details.comment)

    return render
