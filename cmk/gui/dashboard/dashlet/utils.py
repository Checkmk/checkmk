#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.store import get_permitted_dashboards_by_owners
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.session import UserContext
from cmk.gui.token_auth import AuthToken
from cmk.gui.utils.roles import UserPermissions


def get_dashlet_config_via_token(
    ctx: PageContext, token: AuthToken, widget_id: str
) -> DashletConfig:
    board_name = token.details.dashboard_name
    try:
        with UserContext(
            token.issuer, UserPermissions.from_config(ctx.config, permission_registry)
        ):
            board = get_permitted_dashboards_by_owners()[board_name][token.details.owner]
    except KeyError:
        raise MKUserError(
            "invalid_dashboard",
            _("No dashboard found for the given dashboard name and/or dashboard owner"),
        )

    widgets = {f"{board_name}-{idx}": d_config for idx, d_config in enumerate(board["dashlets"])}
    if dashlet_config := widgets.get(widget_id):
        return dashlet_config
    raise MKUserError(
        "widget_config",
        _("The given widget id does not match any of this dashboard's widgets"),
    )
