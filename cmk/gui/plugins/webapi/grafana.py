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
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.plugins.metrics.utils import perfvar_translation, metric_info


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
