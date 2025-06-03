#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parent scan

For the monitoring to be able to determine the UNREACH state, it must know which path it can use to
contact each individual host. For this purpose, one or more so-called parent hosts can be specified
for each host. Parents can be set up automatically via the Parent scan.

Additional information about the parents and the parent scan can be found in the
[Checkmk documentation](https://docs.checkmk.com/latest/en/hosts_structure.html#parents).
"""

from collections.abc import Mapping
from typing import Any, assert_never

from cmk.gui.background_job import BackgroundJob
from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.parent_scan.request_schemas import ParentScan
from cmk.gui.openapi.endpoints.parent_scan.response_schemas import BackgroundJobStatusObject
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainType
from cmk.gui.openapi.utils import serve_json
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.parent_scan import (
    ParentScanBackgroundJob,
    ParentScanSettings,
    start_parent_scan,
    WhereChoices,
)


@Endpoint(
    constructors.domain_type_action_href("parent_scan", "start"),
    "cmk/start",
    method="post",
    additional_status_codes=[409],
    request_schema=ParentScan,
    response_schema=BackgroundJobStatusObject,
)
def start_parent_scan_background_job(params: Mapping[str, Any]) -> Response:
    """Start the parent scan background job"""
    body = params["body"]
    body_gateway = body["gateway_hosts"]
    where: WhereChoices
    match body_gateway["option"]:
        case "create_in_folder":
            where = "gateway_folder"
            alias = body_gateway["hosts_alias"]
            gateway_folder_path = body_gateway["folder"].path()
        case "create_in_host_location":
            where = "there"
            alias = body["gateway_hosts"]["hosts_alias"]
            gateway_folder_path = None
        case "no_gateway_hosts":
            where = "nowhere"
            alias = ""
            gateway_folder_path = None
        case other:
            assert_never(other)

    parent_scan_job = ParentScanBackgroundJob()
    if (
        result := start_parent_scan(
            hosts=[Host.load_host(name) for name in body["host_names"]],
            job=parent_scan_job,
            settings=ParentScanSettings(
                where=where,
                alias=alias,
                timeout=body["performance"]["responses_timeout"],
                probes=body["performance"]["hop_probes"],
                max_ttl=body["performance"]["max_gateway_distance"],
                force_explicit=body["configuration"]["force_explicit_parents"],
                ping_probes=body["performance"]["ping_probes"],
                gateway_folder_path=gateway_folder_path,
            ),
            site_configs=active_config.sites,
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )
    ).is_error():
        raise result.error
    return _serve_background_job(parent_scan_job, "parent_scan")


def _serve_background_job(job: BackgroundJob, domain_type: DomainType) -> Response:
    job_id = job.get_job_id()
    status = job.get_status()
    return serve_json(
        constructors.domain_object(
            domain_type=domain_type,
            identifier=job_id,
            title=f"Background job {job_id} {'is active' if job.is_active() else 'is finished'}",
            extensions={
                "active": job.is_active(),
                "state": status.state,
                "logs": {
                    "result": status.loginfo["JobResult"],
                    "progress": status.loginfo["JobProgressUpdate"],
                },
            },
            deletable=False,
            editable=False,
        )
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(
        start_parent_scan_background_job, ignore_duplicates=ignore_duplicates
    )
