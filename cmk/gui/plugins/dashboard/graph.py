#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import livestatus

import cmk.gui.sites as sites
from cmk.gui.exceptions import MKUserError
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

from cmk.gui.plugins.metrics.html_render import default_dashlet_graph_render_options
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options, transform_graph_render_options


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

    @classmethod
    def vs_parameters(cls):
        return Dictionary(
            title=_('Properties'),
            render='form',
            optional_keys=[],
            elements=cls._parameter_elements,
        )

    @classmethod
    def _parameter_elements(cls):
        elements = [
            # TODO: Cleanup: switch to generic Timerange() valuespec!
            ("timerange",
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
             )),
            ("source", Integer(
                title=_("Source (n'th graph)"),
                default_value=1,
                minvalue=1,
            )),
        ]

        elements += [
            ("graph_render_options",
             vs_graph_render_options(
                 default_values=default_dashlet_graph_render_options,
                 exclude=[
                     "show_time_range_previews",
                     "title_format",
                 ],
             )),
        ]

        return elements

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
        host = self._dashlet_spec['context'].get('host', html.request.var("host"))
        if not host:
            raise MKUserError('host', _('Missing needed host parameter.'))

        service = self._dashlet_spec['context'].get('service')
        if not service:
            service = "_HOST_"

        # When the site is available via URL context, use it. Otherwise it is needed
        # to check all sites for the requested host
        if html.request.has_var('site'):
            site = html.request.var('site')
        else:
            with sites.prepend_site():
                query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
                try:
                    site = sites.live().query_value(query)
                except livestatus.MKLivestatusNotFoundError:
                    raise MKUserError("host", _("The host could not be found on any active site."))

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        timerange = self._dashlet_spec.get('timerange', '1')

        graph_identification = ("template", {
            "site": site,
            "host_name": host,
            "service_description": service,
            "graph_index": self._dashlet_spec["source"] - 1,
        })

        # Be compatible to pre 1.5.0i2 format
        # TODO: Do this conversion during __init__() or during config loading
        if "graph_render_options" not in self._dashlet_spec:
            self._dashlet_spec["graph_render_options"] = transform_graph_render_options({
                "show_legend": self._dashlet_spec.pop("show_legend", False),
                "show_service": self._dashlet_spec.pop("show_service", True),
            })

        graph_render_options = self._dashlet_spec["graph_render_options"]
        graph_render_options.setdefault(
            "title_format",
            self._dashlet_spec.get("title_format",
                                   default_dashlet_graph_render_options["title_format"]))

        return "dashboard_render_graph(%d, %s, %s, '%s')" % \
                (self._dashlet_id, json.dumps(graph_identification),
                 json.dumps(graph_render_options), timerange)

    def show(self):
        html.div("", id_="dashlet_graph_%d" % self._dashlet_id)
