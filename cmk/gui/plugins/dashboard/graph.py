#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import livestatus
from typing import (
    Iterable,
    Optional,
)

import cmk.gui.visuals as visuals
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
)

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)

from cmk.gui.plugins.dashboard.utils import (
    DashboardConfig,
    DashboardName,
    DashletConfig,
    DashletId,
    macro_mapping_from_context,
)

from cmk.gui.plugins.metrics.html_render import default_dashlet_graph_render_options, resolve_graph_recipe
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options
from cmk.utils.macros import MacroMapping


@dashlet_registry.register
class GraphDashlet(Dashlet):
    """Dashlet for rendering a single performance graph"""
    @classmethod
    def type_name(cls):
        return "pnpgraph"

    @classmethod
    def title(cls):
        return _("Performance Graph")

    @classmethod
    def description(cls):
        return _("Displays a performance graph of a host or service.")

    @classmethod
    def sort_index(cls):
        return 20

    @classmethod
    def initial_refresh_interval(cls):
        return 60

    @classmethod
    def initial_size(cls):
        return (60, 21)

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return ["host", "service"]

    @classmethod
    def has_context(cls):
        return True

    def display_title(self) -> str:
        return self._dashlet_spec.get("title",
                                      self._dashlet_spec.get("_graph_title") or self.title())

    def __init__(self, dashboard_name: DashboardName, dashboard: DashboardConfig,
                 dashlet_id: DashletId, dashlet: DashletConfig) -> None:
        super().__init__(dashboard_name=dashboard_name,
                         dashboard=dashboard,
                         dashlet_id=dashlet_id,
                         dashlet=dashlet)

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        self._dashlet_spec.setdefault('timerange', '1')

        self._init_exception = None
        try:
            self._init_graph()
        except Exception as exc:
            # Passes error otherwise exception wont allow to enter dashlet editor
            self._init_exception = exc

    def _init_graph(self):
        context = visuals.get_merged_context(
            visuals.get_context_from_uri_vars(["host", "service"], self.single_infos()),
            self._dashlet_spec["context"])
        self._dashlet_spec["_graph_identification"] = self.graph_identification(context)

        graph_recipes = resolve_graph_recipe(self._dashlet_spec["_graph_identification"])
        if isinstance(graph_recipes, list) and graph_recipes:
            self._dashlet_spec["_graph_title"] = graph_recipes[0]["title"]
        else:
            raise MKGeneralException(_("Failed to calculate a graph recipe."))

    @staticmethod
    def _resolve_site(host):
        # When the site is available via URL context, use it. Otherwise it is needed
        # to check all sites for the requested host
        if html.request.has_var('site'):
            return html.request.var('site')

        with sites.prepend_site():
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
            try:
                return sites.live().query_value(query)
            except livestatus.MKLivestatusNotFoundError:
                raise MKUserError("host", _("The host could not be found on any active site."))

    def graph_identification(self, context):
        host = context.get("host")
        if not host:
            raise MKUserError('host', _('Missing needed host parameter.'))

        service = context.get("service")
        if not service:
            service = "_HOST_"

        site = self._resolve_site(host)

        return ("template", {
            "site": site,
            "host_name": host,
            "service_description": service,
            "graph_index": self._dashlet_spec["source"] - 1,
        })

    @classmethod
    def vs_parameters(cls):
        return Dictionary(
            title=_('Properties'),
            render='form',
            optional_keys=[],
            elements=cls._parameter_elements,
        )

    @staticmethod
    def _vs_timerange():
        # TODO: Cleanup: switch to generic Timerange() valuespec!
        return ("timerange",
                DropdownChoice(
                    title=_('Timerange'),
                    default_value='1',
                    choices=[
                        ("0", _("4 Hours")),
                        ("1", _("25 Hours")),
                        ("2", _("One Week")),
                        ("3", _("One Month")),
                        ("4", _("One Year")),
                    ],
                ))

    @classmethod
    def _parameter_elements(cls):
        return [
            cls._vs_timerange(),
            ("source", Integer(
                title=_("Source (n'th graph)"),
                default_value=1,
                minvalue=1,
            )),
            ("graph_render_options",
             vs_graph_render_options(
                 default_values=default_dashlet_graph_render_options,
                 exclude=[
                     "show_time_range_previews",
                     "title_format",
                     "show_title",
                 ],
             )),
        ]

    @classmethod
    def script(cls):
        return """
var dashlet_offsets = {};
function dashboard_render_graph(nr, graph_identification, graph_render_options, timerange)
{
    // Get the target size for the graph from the inner dashlet container
    var inner = document.getElementById('dashlet_inner_' + nr);
    var c_w = inner.clientWidth;
    var c_h = inner.clientHeight;

    var post_data = "spec=" + encodeURIComponent(JSON.stringify(graph_identification))
                  + "&render=" + encodeURIComponent(JSON.stringify(graph_render_options))
                  + "&timerange=" + encodeURIComponent(timerange)
                  + "&width=" + c_w
                  + "&height=" + c_h
                  + "&id=" + nr;

    cmk.ajax.call_ajax("graph_dashlet.py", {
        post_data        : post_data,
        method           : "POST",
        response_handler : handle_dashboard_render_graph_response,
        handler_data     : nr,
    });
}

function handle_dashboard_render_graph_response(handler_data, response_body)
{
    var nr = handler_data;
    var container = document.getElementById('dashlet_graph_' + nr);
    container.innerHTML = response_body;
    cmk.utils.execute_javascript_by_object(container);
}

"""

    def on_resize(self):
        return self._reload_js()

    def on_refresh(self):
        return self._reload_js()

    def _reload_js(self):
        if any(prop not in self._dashlet_spec
               for prop in ["_graph_identification", "graph_render_options", "timerange"]):
            return ""

        return "dashboard_render_graph(%d, %s, %s, '%s')" % (
            self._dashlet_id,
            json.dumps(self._dashlet_spec["_graph_identification"]),
            json.dumps(self._dashlet_spec["graph_render_options"]),
            self._dashlet_spec['timerange'],
        )

    def show(self):
        if self._init_exception:
            raise self._init_exception

        html.div("", id_="dashlet_graph_%d" % self._dashlet_id)

    def _get_macro_mapping(self, title: str) -> MacroMapping:
        context = self.context
        site = self._get_site_from_dashlet_spec()
        if site:
            context["site"] = site
        macro_mapping = macro_mapping_from_context(
            context,
            self.single_infos(),
            self.display_title(),
        )
        macro_mapping["$GRAPH_TITLE$"] = self._dashlet_spec["_graph_title"]
        return macro_mapping

    def _get_site_from_dashlet_spec(self) -> Optional[str]:
        return self.dashlet_spec["_graph_identification"][1].get("site")

    @staticmethod
    def get_additional_title_macros() -> Iterable[str]:
        yield "$SITE$"
        yield "$GRAPH_TITLE$ " + _("(default title of the graph)")
