#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

"""HTML page handler for generating the (a) dashboard. The name
of the dashboard to render is given in the HTML variable 'name'.
"""

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.htmllib.html import html
from cmk.gui.pages import PageContext
from cmk.gui.token_auth import AuthToken, TokenAuthenticatedPage, TokenId

from .api import convert_internal_relative_dashboard_to_api_model_dict
from .api._utils import DashboardConstants
from .store import (
    get_all_dashboards,
)
from .type_defs import DashboardName


class SharedDashboardPage(TokenAuthenticatedPage):
    def get(self, token: AuthToken, ctx: PageContext) -> None:
        details = token.details
        if details.type_ != "dashboard":
            raise ValueError("Invalid token type for shared dashboard page")

        page_shared_dashboard(details.owner, details.dashboard_name, token.token_id, ctx)


def page_shared_dashboard(
    owner: UserId, dashboard_name: DashboardName, token_id: TokenId, ctx: PageContext
) -> None:
    all_dashboards = get_all_dashboards()
    board = all_dashboards[(owner, dashboard_name)]

    # TODO: keep the request lookup for now (potentially to be removed afterwards)
    board_context = visuals.active_context_from_request(["host", "service"], board["context"])
    board["context"] = board_context
    title = visuals.visual_title("dashboard", board, board_context)

    dashboard_properties = {
        "spec": convert_internal_relative_dashboard_to_api_model_dict(board),
        "name": dashboard_name,
        "title": title,
    }

    html.body_start()
    html.begin_page_content(enable_scrollbar=True)
    page_properties = {
        "dashboard": dashboard_properties,
        "dashboard_constants": DashboardConstants.dict_output(),
        "url_params": {"ifid": ctx.request.get_ascii_input("ifid")},
        "token_value": token_id,
    }
    html.vue_component("cmk-shared-dashboard", data=page_properties)
