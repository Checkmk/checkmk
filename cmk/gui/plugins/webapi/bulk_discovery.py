#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any, Dict, List

from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.webapi.utils import api_call_collection_registry, APICallCollection
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    DiscoveryHost,
    get_tasks,
    vs_bulk_discovery,
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
                    "mode",
                    "use_cache",
                    "do_scan",
                    "ignore_single_check_errors",
                    "bulk_size",
                ],
                "required_permissions": ["wato.services"],
            },
            "bulk_discovery_status": {
                "handler": self._bulk_discovery_status,
                "required_permissions": ["wato.services"],
            },
        }

    def _bulk_discovery_start(self, request):
        job = BulkDiscoveryBackgroundJob()
        if job.is_active():
            raise MKUserError(
                None,
                _(
                    "A bulk discovery job is already running. Please use the "
                    '"bulk_discovery_status" call to get the curent status.'
                ),
            )

        mode, do_scan, bulk_size, error_handling = self._get_parameters_from_request(request)
        tasks = get_tasks(self._get_hosts_from_request(request), bulk_size)

        try:
            job.set_function(job.do_execute, mode, do_scan, error_handling, tasks)
            job.start()
            return {
                "started": True,
            }
        except Exception as e:
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(None, _("Failed to start discovery: %s") % e)

    def _get_parameters_from_request(self, request):
        """Get and verify discovery parameters from the request

        The API call only makes a part of all bulk discovery parameters configurable
        because the API call currently only operates on a list of given hostnames where
        a lot of the GUI options are not relevant for. For a consistent parameter handling
        we use the valuespec here."""
        params: Dict[str, Any] = copy.deepcopy(config.bulk_discovery_default_settings)

        params["mode"] = request.get("mode", params["mode"])

        params["performance"] = (
            request.get("do_scan", params["performance"][0]),
            int(request.get("bulk_size", params["performance"][1])),
        )

        params["error_handling"] = request.get(
            "ignore_single_check_errors", params["error_handling"]
        )

        vs_bulk_discovery().validate_value(params, "")
        return (
            params["mode"],
            params["performance"][0],
            params["performance"][1],
            params["error_handling"],
        )

    def _get_hosts_from_request(self, request: Dict) -> List[DiscoveryHost]:
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
            "is_active": job.is_active(),
            "job": {
                "state": status["state"],
                "result_msg": "\n".join(status["loginfo"]["JobResult"]),
                "output": "\n".join(status["loginfo"]["JobProgressUpdate"]),
            },
        }
