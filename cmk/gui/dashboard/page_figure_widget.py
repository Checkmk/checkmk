#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import override

from cmk.gui.dashboard import dashlet_registry
from cmk.gui.dashboard.api import (
    FigureDashletConfig,
    FigureRequestInternal,
    get_validated_internal_figure_request,
)
from cmk.gui.dashboard.dashlet.dashlets.stats import (
    EventStatsDashletDataGenerator,
    HostStatsDashletDataGenerator,
    ServiceStatsDashletDataGenerator,
)
from cmk.gui.dashboard.token_util import (
    DashboardTokenAuthenticatedJsonPage,
    get_dashboard_widget_by_id,
    impersonate_dashboard_token_issuer,
    InvalidWidgetError,
)
from cmk.gui.figures import create_figures_response, FigureResponseData
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.token_auth import AuthToken, DashboardToken

__all__ = ["FigureWidgetPage", "FigureWidgetTokenAuthPage"]

from cmk.gui.utils.roles import UserPermissions

GENERATOR_BY_FIGURE_TYPE: Mapping[
    str,
    Callable[..., FigureResponseData],
] = {
    "eventstats": EventStatsDashletDataGenerator.generate_response_data,
    "hoststats": HostStatsDashletDataGenerator.generate_response_data,
    "servicestats": ServiceStatsDashletDataGenerator.generate_response_data,
}


class FigureWidgetPage(AjaxPage):
    @classmethod
    def ident(cls) -> str:
        return "widget_figure"

    @classmethod
    def get_data_generator(cls, figure_type_name: str) -> Callable[..., FigureResponseData]:
        if not (generator := GENERATOR_BY_FIGURE_TYPE.get(figure_type_name)):
            raise KeyError(
                _("No data generator found for figure type name '%s'") % figure_type_name
            )
        return generator

    @override
    def page(self, ctx: PageContext) -> PageResult:
        request_data: FigureRequestInternal = get_validated_internal_figure_request(ctx)
        dashlet_config: FigureDashletConfig = request_data.dashlet_config
        dashlet_config.update(
            {
                "context": request_data.context,
                "single_infos": request_data.single_infos,
            }
        )
        if (title := request_data.general_settings.get("title")) is not None:
            dashlet_config.update(
                {
                    "show_title": title["show_title"],
                    "title": title["text"],
                    "title_url": title.get("url", ""),
                }
            )

        return create_figures_response(
            self.get_data_generator(request_data.dashlet_config["type"])(
                dashlet_config,
                request_data.context,
                request_data.single_infos,
            )
        )


class FigureWidgetTokenAuthPage(DashboardTokenAuthenticatedJsonPage):
    @classmethod
    def ident(cls) -> str:
        return "widget_figure_token_auth"

    @classmethod
    def get_data_generator(cls, figure_type_name: str) -> Callable[..., FigureResponseData]:
        return FigureWidgetPage.get_data_generator(figure_type_name)

    @override
    def _post(
        self, token: AuthToken, token_details: DashboardToken, ctx: PageContext
    ) -> PageResult:
        widget_id = ctx.request.get_str_input_mandatory("widget_id")
        with impersonate_dashboard_token_issuer(
            token.issuer,
            token_details,
            UserPermissions.from_config(ctx.config, permission_registry),
        ) as issuer:
            dashboard = issuer.load_dashboard()

        widget_config = get_dashboard_widget_by_id(dashboard, widget_id)
        try:
            widget_type = dashlet_registry[widget_config["type"]]
            data_generator = self.get_data_generator(widget_config["type"])
        except KeyError:
            # likely an edition downgrade where the figure type is not available anymore
            raise InvalidWidgetError(disable_token=True) from None

        widget = widget_type(widget_config, dashboard.get("context"))
        return create_figures_response(
            data_generator(
                widget_config,
                widget.context,
                widget_config["single_infos"],
            )
        )
