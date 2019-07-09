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

import copy
from typing import Dict, List  # pylint: disable=unused-import

import cmk.gui.config as config
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.webapi import (
    APICallCollection,
    api_call_collection_registry,
)

from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    DiscoveryHost,
    vs_bulk_discovery,
    get_tasks,
)
from cmk.gui.watolib.hosts_and_folders import Host


@api_call_collection_registry.register
class APICallBulkDiscovery(APICallCollection):
    def get_api_calls(self):
        return {
            "bulk_discovery_start": {
                "handler": self._bulk_discovery_start,
                "required_keys": ["hostnames"],
                "optional_keys": [
                    "mode", "use_cache", "do_scan", "ignore_single_check_errors", "bulk_size"
                ],
                "required_permissions": ["wato.services"],
            },
            "bulk_discovery_status": {
                "handler": self._bulk_discovery_status,
                "required_permissions": ["wato.services"],
            }
        }

    def _bulk_discovery_start(self, request):
        job = BulkDiscoveryBackgroundJob()
        if job.is_running():
            raise MKUserError(
                None,
                _("A bulk discovery job is already running. Please use the "
                  "\"bulk_discovery_status\" call to get the curent status."))

        mode, use_cache, do_scan, bulk_size, error_handling = self._get_parameters_from_request(
            request)
        tasks = get_tasks(self._get_hosts_from_request(request), bulk_size)

        try:
            job.set_function(job.do_execute, mode, use_cache, do_scan, error_handling, tasks)
            job.start()
            return {
                "started": True,
            }
        except Exception as e:
            logger.error("Failed to start bulk discovery", exc_info=True)
            raise MKUserError(None, _("Failed to start discovery: %s") % e)

    def _get_parameters_from_request(self, request):
        """Get and verify discovery parameters from the request

        The API call only makes a part of all bulk discovery parameters configurable
        because the API call currently only operates on a list of given hostnames where
        a lot of the GUI options are not relevant for. For a consistent parameter handling
        we use the valuespec here."""
        params = copy.deepcopy(config.bulk_discovery_default_settings)

        params["mode"] = request.get("mode", params["mode"])

        params["performance"] = (
            request.get("use_cache", params["performance"][0]),
            request.get("do_scan", params["performance"][1]),
            request.get("bulk_size", params["performance"][2]),
        )

        params["error_handling"] = request.get("ignore_single_check_errors",
                                               params["error_handling"])

        vs_bulk_discovery().validate_value(params, "")
        return (
            params["mode"],
            params["performance"][0],
            params["performance"][1],
            params["performance"][2],
            params["error_handling"],
        )

    def _get_hosts_from_request(self, request):
        # type: (Dict) -> List[DiscoveryHost]
        if not request["hostnames"]:
            raise MKUserError(None, _("You have to specify some hosts"))

        hosts_to_discover = []
        for host_name in request["hostnames"]:
            host = Host.host(host_name)
            if host is None:
                raise MKUserError(None, _("The host '%s' does not exist") % host_name)
            host.need_permission("write")
            hosts_to_discover.append(DiscoveryHost(host.site_id(), host.folder().path(), host_name))
        return hosts_to_discover

    def _bulk_discovery_status(self, request):
        job = BulkDiscoveryBackgroundJob()
        status = job.get_status()
        return {
            "is_running": job.is_running(),
            "job": {
                "state": status["state"],
                "result_msg": "\n".join(status["loginfo"]["JobResult"]),
                "output": "\n".join(status["loginfo"]["JobProgressUpdate"]),
            },
        }
