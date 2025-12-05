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

import json
from typing import Any

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import Response, response
from cmk.gui.i18n import _
from cmk.gui.pages import PageContext
from cmk.gui.theme.current_theme import theme
from cmk.gui.token_auth import AuthToken, TokenAuthenticatedPage, TokenId

from .api import convert_internal_relative_dashboard_to_api_model_dict
from .api._utils import DashboardConstants
from .store import (
    get_all_dashboards,
)
from .type_defs import DashboardConfig, DashboardName


class SharedDashboardPage(TokenAuthenticatedPage):
    def get(self, token: AuthToken, ctx: PageContext) -> None:
        details = token.details
        if details.type_ != "dashboard":
            raise ValueError("Invalid token type for shared dashboard page")

        page_shared_dashboard(details.owner, details.dashboard_name, token.token_id, ctx)


class SharedDashboardPageComponents:
    page_name: str = "shared_dashboard"

    @staticmethod
    def verify_dashboard_referenced_token(dashboard: DashboardConfig, token_id: str) -> None:
        if dashboard.get("public_token_id") != token_id:
            raise ValueError("Referenced invalid dashboard token")

    @staticmethod
    def dashboard_details(
        owner: UserId, dashboard_name: DashboardName
    ) -> tuple[str, DashboardConfig]:
        all_dashboards = get_all_dashboards()
        board = all_dashboards[(owner, dashboard_name)]

        # TODO: keep the request lookup for now (potentially to be removed afterwards)
        board_context = visuals.active_context_from_request(["host", "service"], board["context"])
        board["context"] = board_context
        title = visuals.visual_title("dashboard", board, board_context)
        return title, board

    @staticmethod
    def html_section(page_properties: dict[str, Any]) -> None:
        html.body_start()
        html.begin_page_content(enable_scrollbar=True)
        html.vue_component("cmk-shared-dashboard", data=page_properties)


def page_shared_dashboard(
    owner: UserId, dashboard_name: DashboardName, token_id: TokenId, ctx: PageContext
) -> None:
    title, board = SharedDashboardPageComponents.dashboard_details(owner, dashboard_name)

    SharedDashboardPageComponents.verify_dashboard_referenced_token(board, token_id)

    dashboard_properties = {
        "spec": convert_internal_relative_dashboard_to_api_model_dict(board),
        "name": dashboard_name,
        "title": title,
    }

    # Make sure ifid is valid JSON to avoid XSS
    try:
        ifid = json.loads(ctx.request.get_ascii_input("ifid") or "")
    except ValueError as e:
        raise MKUserError("ifid", _("Invalid ifid parameter")) from e

    page_properties = {
        "dashboard": dashboard_properties,
        "dashboard_constants": DashboardConstants.dict_output(),
        "url_params": {"ifid": ifid},
        "token_value": token_id,
    }
    SharedDashboardPageComponents.html_section(page_properties)


def page_dashboard_token_invalid(title: str) -> Response:
    def _render_main_logo() -> None:
        html.open_div(class_="cmk_main_logo")
        html.open_a(href="https://checkmk.com", class_="logo_link")
        html.img(
            src=theme.detect_icon_path(
                icon_name="login_logo" if theme.has_custom_logo("login_logo") else "checkmk_logo",
                prefix="",
            ),
            id_="logo",
        )
        html.close_a()
        html.close_div()

    def _render_not_available_image() -> None:
        html.open_div(id_="error_image_container")
        html.img(
            src=theme.detect_icon_path(
                icon_name="site_unreachable",
                prefix="",
            ),
            id_="unavailable_icon",
        )
        html.close_div()  # error_image_container

    def _render_message_text_container() -> None:
        html.open_div(class_="message_text_container")
        html.h1(_("Dashboard not available"))
        html.open_div()
        html.p(_("This shared link is not valid."))
        html.p(_("The access token is invalid or revoked or expired."))
        html.close_div()
        html.close_div()  # message_text_container

    html.body_start(title=title, main_javascript="side")
    html.begin_page_content(enable_scrollbar=False)

    html.open_div(id_="cmk_shared_dashboard_error_page")
    _render_main_logo()

    html.open_div(class_="error_message_container")
    _render_not_available_image()
    _render_message_text_container()
    html.close_div()  # error_message_container

    html.close_div()  # cmk_shared_dashboard_error_page
    html.footer()

    return response
