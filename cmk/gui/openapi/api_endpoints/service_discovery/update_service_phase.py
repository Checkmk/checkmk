#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.gui.watolib.services import Discovery, DiscoveryAction, get_check_table
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import make_pending_changes, SERVICE_DISCOVERY_PHASES
from .models.request_models import UpdateDiscoveryPhaseModel

# TODO: CMK-10911 (permissions)
UPDATE_PHASE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.service_discovery_to_monitored"),
        permissions.Perm("wato.service_discovery_to_ignored"),
        permissions.Perm("wato.service_discovery_to_undecided"),
        permissions.Perm("wato.service_discovery_to_removed"),
        permissions.Perm("wato.see_all_folders"),
    ]
)


def update_service_phase_v1(
    api_context: ApiContext,
    body: UpdateDiscoveryPhaseModel,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter().host)],
        PathParam(
            description="The host of the service which shall be updated.",
            example="example.com",
            alias="host_name",
        ),
    ],
) -> ApiResponse[None]:
    """Update the phase of a service"""
    user.need_permission("wato.service_discovery_to_monitored")
    user.need_permission("wato.service_discovery_to_ignored")
    user.need_permission("wato.service_discovery_to_undecided")
    user.need_permission("wato.service_discovery_to_removed")
    user.need_permission("wato.see_all_folders")

    _update_single_service_phase(
        SERVICE_DISCOVERY_PHASES[body.target_phase],
        host,
        body.check_type,
        body.service_item,
        automation_config=make_automation_config(api_context.config.sites[host.site_id()]),
        user_permission_config=api_context.config.user_permissions().to_serializable_config(),
        pprint_value=api_context.config.wato_pprint_config,
        debug=api_context.config.debug,
        use_git=api_context.config.wato_use_git,
        pending_changes=make_pending_changes(
            site_configs=api_context.config.sites,
            use_git=api_context.config.wato_use_git,
            local_site=omd_site(),
            acting_user=user.id,
        ),
    )
    return ApiResponse(body=None, status_code=204)


def _update_single_service_phase(
    target_phase: str,
    host: Host,
    check_type: str,
    service_item: str | None,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
    pending_changes: PendingChanges,
) -> None:
    action = DiscoveryAction.SINGLE_UPDATE
    Discovery(
        host=host,
        action=action,
        update_target=target_phase,
        selected_services=((check_type, service_item),),
        user_need_permission=user.need_permission,
    ).do_discovery(
        get_check_table(
            host,
            action,
            automation_config=automation_config,
            user_permission_config=user_permission_config,
            raise_errors=False,
            debug=debug,
            use_git=use_git,
            pending_changes=pending_changes,
        ),
        host.name(),
        automation_config=automation_config,
        pprint_value=pprint_value,
        debug=debug,
        use_git=use_git,
        pending_changes=pending_changes,
    )


ENDPOINT_UPDATE_SERVICE_PHASE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("host", "{host_name}", "update_discovery_phase"),
        link_relation=".../modify",
        method="put",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=UPDATE_PHASE_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_service_phase_v1)},
)
