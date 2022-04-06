#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any, Dict, List, Tuple

from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import active_config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.webapi.utils import api_call_collection_registry, APICallCollection
from cmk.gui.watolib.bulk_discovery import (
    bulk_discovery_job_status,
    BulkDiscoveryBackgroundJob,
    BulkSize,
    DiscoveryHost,
    DiscoveryMode,
    DoFullScan,
    IgnoreErrors,
    prepare_hosts_for_discovery,
    start_bulk_discovery,
    vs_bulk_discovery,
)


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

        discovery_mode, do_full_scan, bulk_size, ignore_errors = self._get_parameters_from_request(
            request
        )
        try:
            start_bulk_discovery(
                job,
                self._get_hosts_from_request(request),
                discovery_mode,
                do_full_scan,
                ignore_errors,
                bulk_size,
            )
        except Exception as e:
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(None, _("Failed to start discovery: %s") % e)

        return {
            "started": True,
        }

    def _get_parameters_from_request(
        self, request
    ) -> Tuple[DiscoveryMode, DoFullScan, BulkSize, IgnoreErrors]:
        """Get and verify discovery parameters from the request

        The API call only makes a part of all bulk discovery parameters configurable
        because the API call currently only operates on a list of given hostnames where
        a lot of the GUI options are not relevant for. For a consistent parameter handling
        we use the valuespec here."""
        params: Dict[str, Any] = copy.deepcopy(active_config.bulk_discovery_default_settings)

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
            DiscoveryMode(params["mode"]),
            DoFullScan(params["performance"][0]),
            BulkSize(params["performance"][1]),
            IgnoreErrors(params["error_handling"]),
        )

    def _get_hosts_from_request(self, request: Dict) -> List[DiscoveryHost]:
        if not (hostnames := request["hostnames"]):
            raise MKUserError(None, _("You have to specify some hosts"))

        return prepare_hosts_for_discovery(hostnames)

    def _bulk_discovery_status(self, request):
        job = BulkDiscoveryBackgroundJob()
        status_details = bulk_discovery_job_status(job)
        return {
            "is_active": status_details["is_active"],
            "job": {
                "state": status_details["job_state"],
                "result_msg": "\n".join(status_details["logs"]["result"]),
                "output": "\n".join(status_details["logs"]["progress"]),
            },
        }
