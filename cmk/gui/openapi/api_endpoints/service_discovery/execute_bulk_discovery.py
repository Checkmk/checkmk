#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site
from cmk.checkengine.discovery import DiscoverySettings
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.background_job import BACKGROUND_JOB_FAMILY
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    BulkSize,
    DoFullScan,
    IgnoreErrors,
    prepare_hosts_for_discovery,
    start_bulk_discovery,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree

from ._family import SERVICE_DISCOVERY_FAMILY
from .models.request_models import BulkDiscoveryModel

# `prepare_hosts_for_discovery` calls `host.permissions.need_permission("write")`,
# which checks `wato.all_folders` (shortcut) then `wato.edit_hosts` (required if no
# all_folders) — both must be declared so the framework's PermissionValidator allows
# them.
BULK_DISCOVERY_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Optional(permissions.Perm("wato.all_folders")),
        permissions.Optional(permissions.Perm("wato.edit_hosts")),
    ]
)


def execute_bulk_discovery_v1(
    api_context: ApiContext,
    body: BulkDiscoveryModel,
) -> ApiResponse[None]:
    """Start a bulk discovery job

    This endpoint will start a bulk discovery background job. Only one bulk discovery job can run
    at a time. An active bulk discovery job will block other bulk discovery jobs from running until
    the active job is finished.
    """
    job = BulkDiscoveryBackgroundJob()

    options = body.options
    discovery_settings = DiscoverySettings(
        update_host_labels=options.update_host_labels,
        add_new_services=options.monitor_undecided_services,
        remove_vanished_services=options.remove_vanished_services,
        update_changed_service_labels=options.update_service_labels,
        update_changed_service_parameters=options.update_service_parameters,
    )
    hosts_to_discover = prepare_hosts_for_discovery(
        folder_tree(), body.hostnames, api_context.config.sites
    )
    if (
        result := start_bulk_discovery(
            job,
            hosts_to_discover,
            discovery_settings,
            DoFullScan(body.do_full_scan),
            IgnoreErrors(body.ignore_errors),
            BulkSize(body.bulk_size),
            api_context.config.user_permissions().to_serializable_config(),
            pprint_value=api_context.config.wato_pprint_config,
            debug=api_context.config.debug,
            use_git=api_context.config.wato_use_git,
            activation_site_configs=activation_sites(api_context.config.sites),
            local_site=omd_site(),
            acting_user=user.id,
        )
    ).is_error():
        raise result.error

    return ApiResponse(
        body=None,
        status_code=303,
        headers={
            "Location": path_to_endpoint(
                family=BACKGROUND_JOB_FAMILY.name,
                link_relation="cmk/show",
                version=api_context.version,
                parameters={"job_id": job.get_job_id()},
            )
        },
    )


ENDPOINT_EXECUTE_BULK_DISCOVERY = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("discovery_run", "bulk-discovery-start"),
        link_relation="cmk/activate",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=BULK_DISCOVERY_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=execute_bulk_discovery_v1,
            additional_status_codes=[303],
            status_descriptions={
                303: (
                    "The bulk discovery job has been started in the background. "
                    "Redirecting to the 'Get background job status snapshot' endpoint."
                ),
            },
        )
    },
)
