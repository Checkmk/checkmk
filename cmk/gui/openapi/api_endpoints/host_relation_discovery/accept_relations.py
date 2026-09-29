#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.host_relation_scan import (
    accepted_pairs,
    AcceptedScan,
    load_scan,
    RelationDiscoveryBackgroundJob,
    start_relation_linking,
    UnknownJob,
)

from ._family import HOST_RELATION_DISCOVERY_FAMILY
from ._shared import invalid_request, need_discovery_permissions, PERMISSIONS, unknown_job
from .models.request_models import AcceptRequestModel
from .models.response_models import RelationJobModel


def accept_host_relations(api_context: ApiContext, body: AcceptRequestModel) -> RelationJobModel:
    """Store what was accepted of a scan

    Starts a background job; ask the job endpoint for its progress and its summary. Only the
    relations of the scan named are stored, as the scan found them - it is not run again to
    find further ones.
    """
    need_discovery_permissions()
    accepted = AcceptedScan(
        scan_id=body.scan_id,
        findings=body.findings,
        excluded=body.excluded,
        answers=body.answers,
        resolutions=body.resolutions,
    )
    try:
        scanned = load_scan(body.scan_id)
    except UnknownJob as exc:
        raise unknown_job(body.scan_id) from exc
    if scanned is None:
        raise ProblemException(
            status=409, title="The scan has not finished", detail="Wait for it, or scan again."
        )
    try:
        accepted_pairs(scanned, accepted)
    except ValueError as exc:
        raise invalid_request(str(exc)) from exc

    job = RelationDiscoveryBackgroundJob()
    if (
        result := start_relation_linking(
            job,
            accepted,
            UserPermissionSerializableConfig.from_global_config(active_config),
            site_configs=api_context.config.sites,
            wato_hide_folders_without_read_permissions=api_context.config.wato_hide_folders_without_read_permissions,
            wato_host_attrs=api_context.config.wato_host_attrs,
            tags=api_context.config.tags.get_dict_format(),
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
            # Resolved in the request: activation_sites() reads the logged-in user, which
            # the background process has none of before its own context is up.
            activation_site_configs=activation_sites(active_config.sites),
            local_site=omd_site(),
            acting_user=user.id,
        )
    ).is_error():
        raise ProblemException(
            status=409,
            title="Could not start storing the relations",
            detail=str(result.error),
        )

    return RelationJobModel(job_id=job.get_job_id())


ENDPOINT_ACCEPT_RELATIONS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_relation_discovery", "accept"),
        link_relation="cmk/start",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_RELATION_DISCOVERY_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=accept_host_relations)},
)
