#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts (internal)

WARNING: Use at your own risk, not supported.
"""

from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site

from cmk.utils.agent_registration import (
    connection_mode_from_host_config,
    get_uuid_link_manager,
    HostAgentConnectionMode,
)

from cmk.gui.agent_registration import PERMISSION_SECTION_AGENT_REGISTRATION
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.host_internal.request_schemas import LinkHostUUID, RegisterHost
from cmk.gui.openapi.endpoints.host_internal.response_schemas import (
    ConnectionMode,
    HostConfigSchemaInternal,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.hosts_and_folders import Host

permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_AGENT_REGISTRATION,
        name="register_any_existing_host",
        title=_l("Register any existing host"),
        description=_l("This permission allows the registration of any existing host."),
        defaults=["admin", "agent_registration"],
    )
)


permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_AGENT_REGISTRATION,
        name="register_managed_existing_host",
        title=_l("Register managed existing host"),
        description=_l(
            "This permission allows the registration of any existing host the user is a contact of."
        ),
        defaults=["admin", "agent_registration"],
    )
)


@Endpoint(
    constructors.object_action_href(
        "host_config_internal",
        "{host_name}",
        action_name="register",
    ),
    "cmk/register",
    method="put",
    tag_group="Checkmk Internal",
    additional_status_codes=[403, 404, 405],
    status_descriptions={
        403: "You do not have the permissions to register this host.",
        405: "This host cannot be registered on this site.",
    },
    path_params=[HOST_NAME],
    request_schema=RegisterHost,
    response_schema=ConnectionMode,
    permissions_required=permissions.AnyPerm(
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
    ),
)
def register_host(params: Mapping[str, Any]) -> Response:
    """Register an existing host, ie. link it to a UUID"""
    host_name = params["host_name"]
    host = _verified_host(host_name)
    connection_mode = connection_mode_from_host_config(host.effective_attributes())
    _link_with_uuid(
        host_name,
        params["body"]["uuid"],
        connection_mode,
    )
    return serve_json({"connection_mode": connection_mode.value})


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


def _check_host_access_permissions(
    host_name: HostName,
    *,
    access_type: Literal["read", "write"],
) -> Host:
    host = Host.load_host(host_name)
    try:
        host.permissions.need_permission(access_type)
    except MKAuthException:
        raise ProblemException(
            status=401,
            title="Unauthorized",
            detail=f"You do not have {access_type} access to the host {host_name}",
        )
    return host


def _link_with_uuid(
    host_name: HostName,
    uuid: UUID,
    connection_mode: HostAgentConnectionMode,
) -> None:
    uuid_link_manager = get_uuid_link_manager()
    uuid_link_manager.create_link(
        host_name,
        uuid,
        push_configured=connection_mode is HostAgentConnectionMode.PUSH,
    )


@Endpoint(
    constructors.object_action_href(
        "host_config_internal",
        "{host_name}",
        action_name="link_uuid",
    ),
    "cmk/link_uuid",
    method="put",
    tag_group="Checkmk Internal",
    additional_status_codes=[401],
    status_descriptions={
        401: "You do not have the permissions to edit this host.",
    },
    path_params=[HOST_NAME],
    request_schema=LinkHostUUID,
    permissions_required=permissions.AnyPerm(
        [
            permissions.Perm("wato.all_folders"),
            permissions.Perm("wato.edit_hosts"),
            permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
        ]
    ),
    output_empty=True,
)
def link_with_uuid(params: Mapping[str, Any]) -> Response:
    """Link a host to a UUID"""
    host_name = params["host_name"]
    connection_mode = connection_mode_from_host_config(
        _check_host_access_permissions(
            host_name,
            access_type="write",
        ).effective_attributes()
    )
    _link_with_uuid(
        host_name := params["host_name"],
        params["body"]["uuid"],
        connection_mode,
    )
    return Response(status=204)


@Endpoint(
    constructors.object_href(
        "host_config_internal",
        "{host_name}",
    ),
    "cmk/show",
    method="get",
    tag_group="Checkmk Internal",
    additional_status_codes=[401],
    status_descriptions={
        401: "You do not have read access to this host.",
    },
    path_params=[HOST_NAME],
    response_schema=HostConfigSchemaInternal,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def show_host(params: Mapping[str, Any]) -> Response:
    """Show a host"""
    host = _check_host_access_permissions(
        params["host_name"],
        access_type="read",
    )
    return serve_json(
        {
            "site": host.site_id(),
            "is_cluster": host.is_cluster(),
        }
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(register_host, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(link_with_uuid, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_host, ignore_duplicates=ignore_duplicates)
