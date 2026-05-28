#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from livestatus import SiteConfigurations

from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    RedirectException,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.gui.watolib.services import (
    get_check_table,
    has_discovery_action_specific_permissions,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
)
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.everythingtype import EVERYTHING

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import (
    APIDiscoveryAction,
    DISCOVERY_ACTION,
    DISCOVERY_PERMISSIONS,
    job_snapshot,
    make_pending_changes,
    serialize_discovery_result,
)
from .models.request_models import DiscoverServicesModel
from .models.response_models import ServiceDiscoveryResultModel

_DISCOVERY_RUNNING_MSG = "A service discovery background job is currently running"


def execute_service_discovery_v1(
    api_context: ApiContext,
    body: DiscoverServicesModel,
) -> ServiceDiscoveryResultModel:
    """Execute a service discovery on a host"""
    user.need_permission("wato.edit")
    host = body.host_name
    discovery_action = APIDiscoveryAction(body.mode)
    return _execute_service_discovery(
        discovery_action,
        host,
        site_configs=api_context.config.sites,
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
        version=api_context.version,
        host_url=api_context.host_url,
    )


def _execute_service_discovery(
    api_discovery_action: APIDiscoveryAction,
    host: Host,
    *,
    site_configs: SiteConfigurations,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
    pending_changes: PendingChanges,
    version: APIVersion,
    host_url: str,
) -> ServiceDiscoveryResultModel:
    snapshot = job_snapshot(host, site_configs, debug=debug)
    if snapshot.is_active:
        raise ProblemException(status=409, title="Conflict", detail=_DISCOVERY_RUNNING_MSG)

    discovery_action = DISCOVERY_ACTION[api_discovery_action.value]
    if not has_discovery_action_specific_permissions(discovery_action, None):
        raise ProblemException(
            status=403,
            title="Permission denied",
            detail="You do not have the necessary permissions to execute this action",
        )
    discovery_result = get_check_table(
        host,
        discovery_action,
        automation_config=automation_config,
        user_permission_config=user_permission_config,
        raise_errors=False,
        debug=debug,
        use_git=use_git,
        pending_changes=pending_changes,
    )
    match api_discovery_action:
        case APIDiscoveryAction.new:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="new",
                update_target="unchanged",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                pending_changes=pending_changes,
            )
        case APIDiscoveryAction.remove:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="vanished",
                update_target="removed",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                pending_changes=pending_changes,
            )
        case APIDiscoveryAction.fix_all:
            discovery_result = perform_fix_all(
                discovery_result=discovery_result,
                host=host,
                raise_errors=False,
                automation_config=automation_config,
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                pending_changes=pending_changes,
            )
        case APIDiscoveryAction.refresh | APIDiscoveryAction.tabula_rasa:
            # The refresh/tabula_rasa modes start a background job and redirect to the
            # 'wait-for-completion' endpoint instead of returning a discovery result body.
            raise RedirectException(
                location=path_to_endpoint(
                    family=SERVICE_DISCOVERY_FAMILY.name,
                    link_relation="cmk/wait-for-completion",
                    version=version,
                    parameters={"host_name": host.name()},
                ),
            )
        case APIDiscoveryAction.only_host_labels:
            discovery_result = perform_host_label_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                host=host,
                raise_errors=False,
                automation_config=automation_config,
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                pending_changes=pending_changes,
            )
        case APIDiscoveryAction.only_service_labels:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="changed",
                update_target="unchanged",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                pending_changes=pending_changes,
            )
        case _:
            assert_never(api_discovery_action)

    return serialize_discovery_result(host, discovery_result, version=version, host_url=host_url)


ENDPOINT_EXECUTE_SERVICE_DISCOVERY = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("service_discovery_run", "start"),
        link_relation=".../update",
        method="post",
    ),
    permissions=EndpointPermissions(required=DISCOVERY_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=execute_service_discovery_v1,
            additional_status_codes=[303, 409],
            status_descriptions={
                303: (
                    "The service discovery background job has been initialized. Redirecting to "
                    "the 'Wait for service discovery completion' endpoint."
                ),
                409: _DISCOVERY_RUNNING_MSG,
            },
        )
    },
)
