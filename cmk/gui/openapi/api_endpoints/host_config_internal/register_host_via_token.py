#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated
from uuid import UUID

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.gui.exceptions import MKAuthException
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
from cmk.gui.openapi.framework.model.converter import (
    HostConverter,
    TypedPlainValidator,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import get_token_store
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.utils.agent_registration import (
    connection_mode_from_host_config,
    HostAgentConnectionMode,
    UUIDLinkManager,
)

from .models.request_models import RegisterHost
from .models.response_models import ConnectionMode

PERMISSIONS_REGISTER_HOST = permissions.AnyPerm(
    [
        permissions.Perm("agent_registration.register_any_existing_host"),
        permissions.Perm("agent_registration.register_managed_existing_host"),
        permissions.AllPerm(
            [
                # read access
                permissions.Optional(permissions.Perm("wato.see_all_folders")),
                # write access
                permissions.AnyPerm(
                    [
                        permissions.Perm("wato.all_folders"),
                        permissions.Perm("wato.edit_hosts"),
                    ]
                ),
            ]
        ),
    ]
)


def register_host_via_token_v1(
    api_context: ApiContext,
    host_name: Annotated[
        HostName,
        TypedPlainValidator(str, HostConverter.host_name),
        PathParam(description="An existing host name.", example="my_host"),
    ],
    body: RegisterHost,
) -> ApiResponse[ConnectionMode]:
    """Register an existing host, i.e. link it to a UUID"""
    if not api_context.token:
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="This endpoint requires token authentication.",
        )
    host = _verified_host(host_name)
    connection_mode = connection_mode_from_host_config(host.effective_attributes())
    _link_with_uuid(
        host_name,
        body.uuid,
        connection_mode,
    )
    get_token_store().delete(api_context.token.token_id)
    return ApiResponse(ConnectionMode(connection_mode=connection_mode))


def _verified_host(host_name: HostName) -> Host:
    host = Host.load_host(host_name)
    _verify_permissions(host)
    _verify_host_properties(host)
    return host


def _verify_permissions(host: Host) -> None:
    if user.may("agent_registration.register_any_existing_host"):
        return
    if user.may("agent_registration.register_managed_existing_host") and host.is_contact(user):
        return

    unathorized_excpt = ProblemException(
        status=403,
        title="Insufficient permissions",
        detail="You have insufficient permissions to register this host. You either need the "
        "explicit permission to register any host, the explict permission to register this host or "
        "read and write access to this host.",
    )

    try:
        host.permissions.need_permission("read")
    except MKAuthException:
        raise unathorized_excpt
    try:
        host.permissions.need_permission("write")
    except MKAuthException:
        raise unathorized_excpt


def _verify_host_properties(host: Host) -> None:
    if host.site_id() != omd_site():
        raise ProblemException(
            status=405,
            title="Wrong site",
            detail=f"This host is monitored on the site {host.site_id()}, but you tried to register it at the site {omd_site()}.",
        )
    if host.is_cluster():
        raise ProblemException(
            status=405,
            title="Cannot register cluster hosts",
            detail="This host is a cluster host. Register its nodes instead.",
        )


def _link_with_uuid(
    host_name: HostName,
    uuid: UUID,
    connection_mode: HostAgentConnectionMode,
) -> None:
    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=cmk.utils.paths.received_outputs_dir,
        data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
        r4r_discoverable_dir=cmk.utils.paths.r4r_discoverable_dir,
        uuid_lookup_dir=cmk.utils.paths.uuid_lookup_dir,
    )
    uuid_link_manager.create_link(
        host_name,
        uuid,
        push_configured=connection_mode is HostAgentConnectionMode.PUSH,
    )


ENDPOINT_REGISTER_HOST_VIA_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href(
            "host_config_internal", "{host_name}", action_name="register_via_token"
        ),
        link_relation="cmk/register_token",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_REGISTER_HOST),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name, group="Checkmk Internal"),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=register_host_via_token_v1)},
    allowed_tokens={"agent_registration"},
)
