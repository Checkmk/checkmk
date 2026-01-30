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

from typing import Any, override

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.htmllib.html import html
from cmk.gui.http import Response, response
from cmk.gui.i18n import _
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.token_auth import AuthToken, DashboardToken, TokenId
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.roles import UserPermissions

from .api import convert_internal_relative_dashboard_to_api_model_dict, DashboardConstants
from .dashlet.registry import dashlet_registry
from .token_util import DashboardTokenAuthenticatedPage, impersonate_dashboard_token_issuer
from .type_defs import DashboardConfig, DashletConfig


class SharedDashboardPage(DashboardTokenAuthenticatedPage):
    @override
    def _get(self, token: AuthToken, token_details: DashboardToken, ctx: PageContext) -> None:
        page_shared_dashboard(token.token_id, token.issuer, token_details, ctx)

    @override
    def _handle_exception(self, exception: Exception, ctx: PageContext) -> PageResult:
        return page_dashboard_token_invalid(_("Token invalid"))


class SharedDashboardPageComponents:
    page_name: str = "shared_dashboard"

    @staticmethod
    def verify_dashboard_referenced_token(dashboard: DashboardConfig, token_id: str) -> None:
        if dashboard.get("public_token_id") != token_id:
            raise ValueError("Referenced invalid dashboard token")

    @staticmethod
    def html_section(page_properties: dict[str, Any]) -> None:
        html.body_start()
        html.begin_page_content(enable_scrollbar=True)
        html.vue_component("cmk-shared-dashboard", data=page_properties)


def _compute_widget_title(widget_config: DashletConfig) -> str:
    widget_type = dashlet_registry[widget_config["type"]]
    widget = widget_type(widget_config)
    return widget.compute_title()


def compute_widget_titles(board: DashboardConfig) -> dict[str, str]:
    """Compute widget titles for all dashlets in a dashboard.

    NOTE: the widget IDs (keys) must match the conversion functions that build the dashboard spec
    """
    return {
        f"{board['name']}-{idx}": _compute_widget_title(widget)
        for idx, widget in enumerate(board["dashlets"])
    }


def _remove_filter_values(context: VisualContext) -> VisualContext:
    """Removes all filter values, while keeping the filters themselves.

    We keep the filters, so that the dashboard knows which filters are configured. This is needed
    to render appropriate error messages when a required filter is missing.
    The only sensitive part are the actual filter values, which we remove.
    """
    return {key: {} for key in context}


def remove_sensitive_filter_information(board: DashboardConfig) -> None:
    """Removes all filter values from the dashboard config.

    This is done to avoid leaking sensitive information in shared dashboards.
    When rendering, all widgets should be referenced by ID and then load their effective filters
    from the config, not whatever the frontend provides. So removing this information here is safe.
    However, other computations may rely on these filters, so this should be done as the last step
    before converting the dashboard to the API model.
    """
    board["context"] = _remove_filter_values(board.get("context", {}))
    for widget in board.get("dashlets", []):
        widget["context"] = _remove_filter_values(widget.get("context", {}))


def page_shared_dashboard(
    token_id: TokenId, token_issuer: UserId, token_details: DashboardToken, ctx: PageContext
) -> None:
    with impersonate_dashboard_token_issuer(
        token_issuer, token_details, UserPermissions.from_config(ctx.config, permission_registry)
    ) as issuer:
        board = issuer.load_dashboard()
        SharedDashboardPageComponents.verify_dashboard_referenced_token(board, token_id)

        widget_titles = compute_widget_titles(board)
        remove_sensitive_filter_information(board)

        # this can end up loading views when computing the used infos,
        # so it needs the impersonation context
        internal_spec = convert_internal_relative_dashboard_to_api_model_dict(board)

    title = visuals.visual_title("dashboard", board, board["context"])
    dashboard_properties = {
        "spec": internal_spec,
        "name": token_details.dashboard_name,
        "owner": token_details.owner,
        "title": title,
    }

    page_properties = {
        "dashboard": dashboard_properties,
        "widget_titles": widget_titles,
        "dashboard_constants": DashboardConstants.dict_output(),
        "url_params": {"ifid": ctx.request.get_ascii_input("ifid")},
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
        html.p(_("The access token is invalid, revoked or expired."))
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
