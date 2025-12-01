#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"
import json
from collections.abc import Callable, Mapping
from typing import override

from cmk.ccc.exceptions import MKException, MKGeneralException
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
from cmk.gui.dashboard.dashlet.utils import get_dashlet_config_via_token
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.figures import create_figures_response, FigureResponseData
from cmk.gui.http import response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.token_auth import AuthToken, TokenAuthenticatedPage
from cmk.gui.utils.json import CustomObjectJSONEncoder

__all__ = ["FigureWidgetPage", "FigureWidgetTokenAuthPage"]


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


class FigureWidgetTokenAuthPage(TokenAuthenticatedPage):
    @classmethod
    def ident(cls) -> str:
        return "widget_figure_token_auth"

    @classmethod
    def get_data_generator(cls, figure_type_name: str) -> Callable[..., FigureResponseData]:
        return FigureWidgetPage.get_data_generator(figure_type_name)

    def post(self, token: AuthToken, ctx: PageContext) -> PageResult:
        response.set_content_type("application/json")
        try:
            if token.details.disabled or (token.details.type_ != "dashboard"):
                raise MKUserError(
                    "invalid_token",
                    _("The provided token is not valid for the requested page."),
                )

            if (widget_id := ctx.request.get_str_input("widget_id")) is None:
                raise MKUserError("widget_id", _("Missing request variable 'widget_id'"))

            dashlet_config = get_dashlet_config_via_token(ctx, token, widget_id)

            action_response = create_figures_response(
                self.get_data_generator(dashlet_config["type"])(
                    dashlet_config,
                    dashlet_config["context"],
                    dashlet_config["single_infos"],
                )
            )

            resp = {"result_code": 0, "result": action_response, "severity": "success"}
        except MKMissingDataError as e:
            resp = {"result_code": 1, "result": str(e), "severity": "success"}
        # I added MKGeneralException during a refactoring, but I did not check if it is needed.
        except (MKException, MKGeneralException, MKUserError) as e:
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        except Exception as e:
            if ctx.config.debug:
                raise
            logger.exception("error calling token authenticated page handler")
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        response.set_data(json.dumps(resp, cls=CustomObjectJSONEncoder))

        return resp
