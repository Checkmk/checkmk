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
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.gui.watolib.services import Discovery, DiscoveryAction, get_check_table
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.web.utils import permission_verification as permissions

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import make_pending_changes, SERVICE_DISCOVERY_PHASES
from .models.request_models import UpdateDiscoveryPhaseModel, UpdateDiscoveryPhaseModelUnstable

UPDATE_PHASE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.services"),
        permissions.Perm("wato.service_discovery_to_monitored"),
        permissions.Perm("wato.service_discovery_to_ignored"),
        permissions.Perm("wato.service_discovery_to_undecided"),
        permissions.Perm("wato.service_discovery_to_removed"),
        # Only used as a shortcut to see hosts without being a contact of their folder.
        permissions.Optional(permissions.Perm("wato.see_all_folders")),
    ]
)

#: The four phases that name a transition a caller may ask for. Every other value the request model
#: still accepts (kept in the stable v1 enum for backwards compatibility) names a state the
#: discovery run classifies a service into, not a target it can be moved to -- applying one deletes
#: the service instead of moving it, so it is refused with a 400 (CMK-38588). The UNSTABLE version
#: narrows the enum itself to exactly these four, so its generated spec never advertises the rest.
_COMMAND_PHASES = frozenset({"monitored", "undecided", "ignored", "removed"})


def update_service_phase_v1(
    api_context: ApiContext,
    body: UpdateDiscoveryPhaseModel,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter(permission_type="setup_read").host)],
        PathParam(
            description="The host of the service which shall be updated.",
            example="example.com",
            alias="host_name",
        ),
    ],
) -> ApiResponse[None]:
    """Update the phase of a service"""
    if body.target_phase not in _COMMAND_PHASES:
        raise ProblemException(
            status=400,
            title="Not a valid target phase",
            detail=f"{body.target_phase!r} is not a phase a service can be moved to. "
            f"Use one of {sorted(_COMMAND_PHASES)}.",
        )
    _update_service_phase(api_context, body.target_phase, body.check_type, body.service_item, host)
    return ApiResponse(body=None, status_code=204)


def update_service_phase_unstable(
    api_context: ApiContext,
    body: UpdateDiscoveryPhaseModelUnstable,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter(permission_type="setup_read").host)],
        PathParam(
            description="The host of the service which shall be updated.",
            example="example.com",
            alias="host_name",
        ),
    ],
) -> ApiResponse[None]:
    """Update the phase of a service"""
    # `target_phase` is narrowed to the four command phases at the model level, so no value check is
    # needed here -- an unaccepted phase is a `literal_error` from the framework before this runs.
    _update_service_phase(api_context, body.target_phase, body.check_type, body.service_item, host)
    return ApiResponse(body=None, status_code=204)


def _update_service_phase(
    api_context: ApiContext,
    target_phase: str,
    check_type: str,
    service_item: str | None,
    host: Host,
) -> None:
    user.need_permission("wato.edit")
    user.need_permission("wato.services")
    user.need_permission("wato.service_discovery_to_monitored")
    user.need_permission("wato.service_discovery_to_ignored")
    user.need_permission("wato.service_discovery_to_undecided")
    user.need_permission("wato.service_discovery_to_removed")

    _update_single_service_phase(
        SERVICE_DISCOVERY_PHASES[target_phase],
        host,
        check_type,
        service_item,
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
    versions={
        APIVersion.V1: EndpointHandler(handler=update_service_phase_v1),
        APIVersion.UNSTABLE: EndpointHandler(handler=update_service_phase_unstable),
    },
)
