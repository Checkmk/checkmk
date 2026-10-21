#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Hosts (internal)

WARNING: Use at your own risk, not supported.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any
from uuid import UUID

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.gui.agent_registration import PERMISSION_SECTION_AGENT_REGISTRATION
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKInsufficientScope, MKUserError
from cmk.gui.fields import HostField
from cmk.gui.http import Response
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.host_internal.request_schemas import RegisterHostRequest
from cmk.gui.openapi.endpoints.host_internal.response_schemas import HostConnectionMode
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.watolib import bakery
from cmk.gui.watolib.agent_registration import (
    link_uuid_of_existing_host,
    UUIDAlreadyLinkedError,
    UUIDOfOpenRequestError,
)
from cmk.gui.watolib.hosts_and_folders import FolderTree, Host, make_folder_tree
from cmk.utils.agent_registration import (
    connection_mode_from_host_config,
    HostAgentConnectionMode,
    RegistrationRoute,
    UUIDRegistration,
)
from cmk.web.utils import permission_verification as permissions

permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_AGENT_REGISTRATION,
        name="register_any_existing_host",
        title=_l("Register any existing host"),
        description=_l(
            "This permission allows to register the Agent Controller for any existing host."
        ),
        defaults=["admin", "agent_registration"],
    )
)


permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_AGENT_REGISTRATION,
        name="register_managed_existing_host",
        title=_l("Register managed existing host"),
        description=_l(
            "This permission allows to register the Agent Controller for any existing host"
            " the user is a contact of."
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
    additional_status_codes=[
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.METHOD_NOT_ALLOWED,
        HTTPStatus.CONFLICT,
    ],
    status_descriptions={
        HTTPStatus.FORBIDDEN: "You do not have the permissions to register this host.",
        HTTPStatus.METHOD_NOT_ALLOWED: "This host cannot be registered on this site.",
        HTTPStatus.CONFLICT: "The UUID is already linked to a host or belongs to an open request"
        " of the automatic registration.",
    },
    path_params=[
        {
            "host_name": HostField(
                description="A host name.",
                should_exist=None,
            )
        }
    ],
    request_schema=RegisterHostRequest,
    response_schema=HostConnectionMode,
    permissions_required=permissions.AllPerm(
        [
            permissions.AnyPerm(
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
            bakery.PERMISSIONS_MAY_REGISTER_FOR_AGENT_UPDATES,
        ]
    ),
)
def register_host(params: Mapping[str, Any]) -> Response:
    """Register an existing host, ie. link it to a UUID"""
    host_name = params["host_name"]
    host = _verified_host(make_folder_tree(active_config), host_name)
    connection_mode = connection_mode_from_host_config(host.effective_attributes())
    _link_registration(host, params["body"]["uuid"], connection_mode)
    return serve_json({"connection_mode": connection_mode.value})


def _link_registration(host: Host, uuid: UUID, connection_mode: HostAgentConnectionMode) -> None:
    try:
        link_uuid_of_existing_host(
            host.name(),
            uuid,
            push_configured=connection_mode is HostAgentConnectionMode.PUSH,
            registration=UUIDRegistration(
                agent_updates_permitted=bakery.may_register_for_agent_updates(
                    user, is_contact=host.is_contact(user)
                ),
                subject=user.ident,
                registration_route=RegistrationRoute.REGISTER,
            ),
        )
    except (UUIDAlreadyLinkedError, UUIDOfOpenRequestError) as exc:
        raise ProblemException(
            status=HTTPStatus.CONFLICT, title="UUID already in use", detail=str(exc)
        ) from exc


def _verified_host(tree: FolderTree, host_name: HostName) -> Host:
    try:
        host = tree.load_host(host_name)

    except MKUserError:
        if not user.may("agent_registration.register_any_existing_host") and not user.may(
            "wato.all_folders"
        ):
            raise ProblemException(
                status=HTTPStatus.FORBIDDEN,
                title="Insufficient permissions",
                detail="You have insufficient permissions to register this host. You either need the "
                "explicit permission to register any host, the explict permission to register this host or "
                "read and write access to this host.",
            )

        raise ProblemException(
            status=HTTPStatus.NOT_FOUND,
            title=HTTPStatus.NOT_FOUND.phrase,
            detail=f"Host {host_name} does not exist.",
        )

    host = tree.load_host(host_name)
    _verify_permissions(host)
    _verify_host_properties(host)
    return host


def _verify_permissions(host: Host) -> None:
    if user.may("agent_registration.register_any_existing_host"):
        return
    if user.may("agent_registration.register_managed_existing_host") and host.is_contact(user):
        return

    unathorized_excpt = ProblemException(
        status=HTTPStatus.FORBIDDEN,
        title="Insufficient permissions",
        detail="You have insufficient permissions to register this host. You either need the "
        "explicit permission to register any host, the explict permission to register this host or "
        "read and write access to this host.",
    )

    try:
        host.permissions.need_permission("read", user)
        host.permissions.need_permission("write", user)
    except MKInsufficientScope:
        raise
    except MKAuthException:
        raise unathorized_excpt


def _verify_host_properties(host: Host) -> None:
    if host.site_id() != omd_site():
        raise ProblemException(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            title="Wrong site",
            detail=f"This host is monitored on the site {host.site_id()}, but you tried to register it at the site {omd_site()}.",
        )
    if host.is_cluster():
        raise ProblemException(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            title="Cannot register cluster hosts",
            detail="This host is a cluster host. Register its nodes instead.",
        )


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(register_host)
