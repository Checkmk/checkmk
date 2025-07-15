#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
from typing import cast

from cmk.ccc.user import UserId

from cmk.gui.config import Config
from cmk.gui.dashboard.type_defs import DashletSize
from cmk.gui.exceptions import MKUserError
from cmk.gui.figures import create_figures_response, FigureResponseData
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import HTTPVariables, SingleInfos
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.valuespec import Dictionary, DictionaryElements, MigrateNotUpdated

from ..store import get_permitted_dashboards_by_owners
from .base import Dashlet, T
from .registry import dashlet_registry

__all__ = ["FigureDashletPage", "ABCFigureDashlet"]


class FigureDashletPage(AjaxPage):
    def page(self, config: Config) -> PageResult:
        dashboard_name = request.get_ascii_input_mandatory("name")
        dashboard_owner = request.get_validated_type_input_mandatory(UserId, "owner")
        try:
            dashboard = get_permitted_dashboards_by_owners()[dashboard_name][dashboard_owner]
        except KeyError:
            raise MKUserError("name", _("The requested dashboard does not exist."))
        # Get context from the AJAX request body (not simply from the dashboard config) to include
        # potential dashboard context given via HTTP request variables
        dashboard["context"] = json.loads(request.get_ascii_input_mandatory("context"))

        dashlet_id = request.get_integer_input_mandatory("id")
        try:
            dashlet_spec = dashboard["dashlets"][dashlet_id]
        except IndexError:
            raise MKUserError("id", _("The element does not exist."))

        try:
            dashlet_type = cast(type[ABCFigureDashlet], dashlet_registry[dashlet_spec["type"]])
        except KeyError:
            raise MKUserError("type", _("The requested element type does not exist."))

        dashlet = dashlet_type(dashboard_name, dashboard_owner, dashboard, dashlet_id, dashlet_spec)
        return create_figures_response(dashlet.generate_response_data())


class ABCFigureDashlet(Dashlet[T], abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    def type_name(cls) -> str:
        return "figure_dashlet"

    @classmethod
    def sort_index(cls) -> int:
        return 95

    @classmethod
    def initial_refresh_interval(cls) -> bool:
        return False

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (56, 40)

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return []

    @classmethod
    def has_context(cls) -> bool:
        return True

    @property
    def instance_name(self) -> str:
        # Note: This introduces the restriction one graph type per dashlet
        return f"{self.type_name()}_{self._dashlet_id}"

    @classmethod
    def vs_parameters(cls) -> MigrateNotUpdated:
        return MigrateNotUpdated(
            valuespec=Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=cls._vs_optional_keys(),
                elements=cls._vs_elements(),
            ),
            migrate=cls._migrate_vs,
        )

    @staticmethod
    def _vs_optional_keys() -> bool | list[str]:
        return False

    @staticmethod
    def _migrate_vs(valuespec_result):
        if "svc_status_display" in valuespec_result:
            # now as code is shared between host and service (svc) dashlet,
            # the `svc_` prefix is removed.
            valuespec_result["status_display"] = valuespec_result.pop("svc_status_display")
        return valuespec_result

    @staticmethod
    def _vs_elements() -> DictionaryElements:
        return []

    @abc.abstractmethod
    def generate_response_data(self) -> FigureResponseData: ...

    @property
    def update_interval(self) -> int:
        return 60

    def on_resize(self):
        return ("if (typeof %(instance)s != 'undefined') {%(instance)s.update_gui();}") % {
            "instance": self.instance_name
        }

    def show(self) -> None:
        self.js_dashlet(figure_type_name=self.type_name())

    def js_dashlet(self, figure_type_name: str) -> None:
        fetch_url = "ajax_figure_dashlet_data.py"
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        # TODO: Would be good to align this scheme with AjaxPage.webapi_request()
        # (a single HTTP variable "request=<json-body>".
        post_body = urlencode_vars(self._dashlet_http_variables())

        html.javascript(
            """
            let figure_%(dashlet_id)d = cmk.figures.figure_registry.get_figure(%(type_name)s);
            let %(instance_name)s = new figure_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.set_dashlet_spec(%(dashlet_spec)s);
            %(instance_name)s.initialize();
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """
            % {
                "type_name": json.dumps(figure_type_name),
                "dashlet_id": self._dashlet_id,
                "dashlet_spec": json.dumps(self.dashlet_spec),
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(post_body),
                "update": self.update_interval,
            }
        )

    def _dashlet_http_variables(self) -> HTTPVariables:
        return [
            ("name", self.dashboard_name),
            ("id", self.dashlet_id),
            ("owner", self.dashboard_owner),
            # Add context to the dashlet's AJAX request body so any dashboard context that is given
            # via HTTP request is not lost in the AJAX call
            ("context", json.dumps(self._dashboard["context"])),
        ]
