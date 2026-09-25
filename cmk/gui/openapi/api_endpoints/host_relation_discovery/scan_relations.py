#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.host_relation_scan import RelationScanBackgroundJob, start_relation_scan

from ._family import HOST_RELATION_DISCOVERY_FAMILY
from ._shared import finding_args, need_discovery_permissions, PERMISSIONS
from .models.request_models import ScanRequestModel
from .models.response_models import RelationJobModel


def scan_host_relations(body: ScanRequestModel) -> RelationJobModel:
    """Find the relations the hosts in Setup speak for

    Starts a background job that reads every host and keeps what it proposes, each proposal
    with the finding it came from and what storing it would do. Ask the job endpoint for the
    summary and the rows endpoint for the proposals. Changes nothing.
    """
    need_discovery_permissions()
    findings = finding_args(body)
    job = RelationScanBackgroundJob()
    if (
        result := start_relation_scan(
            job, findings, UserPermissionSerializableConfig.from_global_config(active_config)
        )
    ).is_error():
        raise ProblemException(
            status=409, title="Could not start the scan", detail=str(result.error)
        )
    return RelationJobModel(job_id=job.get_job_id())


ENDPOINT_SCAN_RELATIONS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_relation_discovery", "scan"),
        link_relation="cmk/compute",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_RELATION_DISCOVERY_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=scan_host_relations)},
)
