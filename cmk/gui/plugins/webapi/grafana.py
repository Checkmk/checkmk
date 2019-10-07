#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import livestatus

from cmk.gui.plugins.webapi import (
    APICallCollection,
    api_call_collection_registry,
)

import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.visuals as visuals
import cmk.gui.availability as availability
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.plugins.metrics.utils import (
    perfvar_translation,
    metric_info,
    get_graph_template_choices,
)
from cmk.gui.plugins.views.utils import (
    data_source_registry,)


@api_call_collection_registry.register
class APICallGrafanaConnector(APICallCollection):
    def get_api_calls(self):
        return {
            "get_user_sites": {
                "handler": self._get_user_sites,
                "locking": False,
            },
            "get_host_names": {
                "handler": self._get_host_names,
                "optional_keys": ["site_id"],
                "locking": False,
            },
            "get_metrics_of_host": {
                "handler": self._get_metrics_of_host,
                "required_keys": ["hostname"],
                "optional_keys": ["site_id"],
                "locking": False,
            },
            "get_graph_recipes": {
                "handler": self._get_graph_recipes,
                "required_keys": ["specification"],
                "locking": False,
            },
            "get_combined_graph_identifications": {
                "handler": self._get_combined_graph_identifications,
                "required_keys": ["single_infos", "datasource", "context"],
                "optional_keys": ["presentation"],
                "locking": False,
            },
            "get_graph_annotations": {
                "handler": self._get_graph_annotations,
                "required_keys": ["start_time", "end_time", "context"],
                "locking": False,
            },
        }

    def _get_user_sites(self, request):
        return config.sorted_sites()

    def _get_host_names(self, request):
        return self._query_for_host_names(request.get("site_id"))

    def _query_for_host_names(self, site_id):
        try:
            sites.live().set_only_sites([site_id] if site_id else None)
            return sites.live().query_column("GET hosts\nColumns: name\n")
        finally:
            sites.live().set_only_sites(None)

    def _get_metrics_of_host(self, request):
        return self._query_for_metrics_of_host(request["hostname"], request.get("site_id"))

    def _query_for_metrics_of_host(self, host_name, site_id):
        if not host_name:
            return {}

        query = ("GET services\n"
                 "Columns: description check_command metrics\n"
                 "Filter: host_name = %s\n" % livestatus.lqencode(host_name))

        response = {}

        try:
            sites.live().set_only_sites([site_id] if site_id else None)
            rows = sites.live().query(query)
        finally:
            sites.live().set_only_sites(None)

        for service_description, check_command, metrics in rows:
            response[service_description] = {
                "check_command": check_command,
                "metrics": self._get_metric_infos(metrics, check_command),
            }

        return response

    def _get_metric_infos(self, service_metrics, check_command):
        metric_infos = {}
        for nr, perfvar in enumerate(service_metrics):
            translated = perfvar_translation(perfvar, check_command)
            name = translated["name"]
            mi = metric_info.get(name, {})
            metric_infos[perfvar] = {
                "index": nr,
                "name": name,
                "title": mi.get("title", name.title()),
            }
        return metric_infos

    def _get_graph_recipes(self, request):
        try:
            from cmk.gui.cee.plugins.metrics.graphs import graph_recipes_for_api_request
        except ImportError:
            raise MKGeneralException(_("Currently not supported with this Check_MK Edition"))
        _graph_data_range, graph_recipes = graph_recipes_for_api_request(request)
        return graph_recipes

    def _get_combined_graph_identifications(self, request):
        try:
            from cmk.gui.cee.plugins.metrics.graphs import (
                combined_graph_presentations,
                matching_combined_graphs,
            )
        except ImportError:
            raise MKGeneralException(_("Currently not supported with this Check_MK Edition"))

        presentation = request.get("presentation", "sum")
        if presentation not in combined_graph_presentations:
            raise MKGeneralException(_("The requested item %s does not exist") % presentation)

        single_infos = request["single_infos"]
        datasource_name = request["datasource"]
        context = request["context"]

        # The grafana connector needs the template title for making them
        # selectable by the user. We extend the graph identification here.
        # Otherwise we would need more API calls
        response = []
        for graph_identification in matching_combined_graphs(datasource_name, single_infos,
                                                             presentation, context):
            graph_template_id = graph_identification[1]["graph_template"]
            graph_title = dict(get_graph_template_choices()).get(graph_template_id,
                                                                 graph_template_id)

            response.append({
                "identification": graph_identification,
                "title": graph_title,
            })
        return response

    def _get_graph_annotations(self, request):
        filter_headers, only_sites = self._get_filter_headers_of_context(datasource_name="services",
                                                                         context=request["context"],
                                                                         single_infos=[])

        return {
            "availability_timelines": self._get_availability_timelines(
                request["start_time"],
                request["end_time"],
                only_sites,
                filter_headers,
            ),
        }

    def _get_filter_headers_of_context(self, datasource_name, context, single_infos):
        try:
            from cmk.gui.cee.plugins.metrics.graphs import get_matching_filters
        except ImportError:
            raise MKGeneralException(_("Currently not supported with this Check_MK Edition"))

        datasource = data_source_registry[datasource_name]()

        # Note: our context/visuals/filters systems is not yet independent of
        # URL variables. This is not nice but needs a greater refactoring, so
        # we need to live with the current situation for the while.
        with html.stashed_vars():
            # add_context_to_uri_vars needs the key "single_infos"
            visuals.add_context_to_uri_vars({
                "context": context,
                "single_infos": single_infos,
            })

            # Prepare Filter headers for Livestatus
            filter_headers = ""
            for filt in get_matching_filters(datasource.infos):
                filter_headers += filt.filter(datasource.table)

            if html.request.var("site"):
                only_sites = [html.request.var("site")]
            else:
                only_sites = None

            return filter_headers, only_sites

    def _get_availability_timelines(self, start_time, end_time, only_sites, filter_headers):
        avoptions = availability.get_default_avoptions()
        timerange = start_time, end_time
        avoptions["range"] = timerange, ""

        # Currently we have now way to show a warning message for _has_reached_logrow_limit
        av_rawdata, _has_reached_logrow_limit = availability.get_availability_rawdata(
            what="service",
            context={},
            filterheaders=filter_headers,
            only_sites=only_sites,
            av_object=None,
            include_output=True,
            include_long_output=False,
            avoptions=avoptions,
        )

        av_data = availability.compute_availability(what="service",
                                                    av_rawdata=av_rawdata,
                                                    avoptions=avoptions)
        return av_data
