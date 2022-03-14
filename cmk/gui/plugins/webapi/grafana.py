#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple

import livestatus

import cmk.gui.availability as availability
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.graph_images import graph_recipes_for_api_request
from cmk.gui.plugins.metrics.utils import (
    get_graph_template_choices,
    metric_info,
    perfvar_translation,
)
from cmk.gui.plugins.views.utils import data_source_registry
from cmk.gui.plugins.webapi.utils import api_call_collection_registry, APICallCollection
from cmk.gui.visuals import cleanup_context_filters, get_filter_headers


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
        return sites.sorted_sites()

    def _get_host_names(self, request):
        return self._query_for_host_names(request.get("site_id"))

    def _query_for_host_names(self, site_id):
        with sites.only_sites(site_id):
            return sites.live().query_column("GET hosts\nColumns: name\n")

    def _get_metrics_of_host(self, request):
        return self._query_for_metrics_of_host(request["hostname"], request.get("site_id"))

    def _query_for_metrics_of_host(self, host_name, site_id):
        if not host_name:
            return {}

        query = (
            "GET services\n"
            "Columns: description check_command metrics\n"
            "Filter: host_name = %s\n" % livestatus.lqencode(host_name)
        )

        response = {}

        with sites.only_sites(site_id):
            rows = sites.live().query(query)

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
        _graph_data_range, graph_recipes = graph_recipes_for_api_request(request)
        return graph_recipes

    def _get_combined_graph_identifications(self, request):
        try:
            from cmk.gui.cee.plugins.metrics.graphs import (
                combined_graph_presentations,
                matching_combined_graphs,
            )
        except ImportError:
            raise MKGeneralException(_("Currently not supported with this Checkmk Edition"))

        if "presentation" not in request:
            request["presentation"] = "sum"
        presentation = request["presentation"]
        if presentation not in combined_graph_presentations:
            raise MKGeneralException(_("The requested item %s does not exist") % presentation)

        # Because grafana connector <= 1.1.0 sends empty string when no site filter is
        # applied, yet cmk takes takes context['site'] as enforced thus "" is an applied site filter
        if "site" in request["context"] and not request["context"]["site"]:
            request["context"].pop("site")

        # The grafana connector needs the template title for making them
        # selectable by the user. We extend the graph identification here.
        # Otherwise we would need more API calls
        response = []
        for graph_identification in matching_combined_graphs(request):
            graph_template_id = graph_identification[1]["graph_template"]
            graph_title = dict(get_graph_template_choices()).get(
                graph_template_id, graph_template_id
            )
            response.append(
                {
                    "identification": graph_identification,
                    "title": graph_title,
                }
            )
        return response

    def _get_graph_annotations(self, request):
        if "host" in request["context"]:
            single_infos = ["host"]
        else:
            single_infos = []

        context = cleanup_context_filters(request["context"], single_infos)

        filter_headers, only_sites = self._get_filter_headers_of_context(
            datasource_name="services", context=context, single_infos=single_infos
        )

        return {
            "availability_timelines": self._get_availability_timelines(
                request["start_time"],
                request["end_time"],
                only_sites,
                filter_headers,
            ),
        }

    def _get_filter_headers_of_context(
        self,
        datasource_name,
        context,
        single_infos,
    ) -> Tuple[str, livestatus.OnlySites]:
        return get_filter_headers("", data_source_registry[datasource_name]().infos, context)

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

        av_data = availability.compute_availability(
            what="service", av_rawdata=av_rawdata, avoptions=avoptions
        )
        return av_data
