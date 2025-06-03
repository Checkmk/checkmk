#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
User Roles

Checkmk always assigns permissions to users via roles — never directly. A role is nothing more than a list of permissions.
It is important that you understand that roles define the level of permissions and not the reference to any hosts or services.
That is what contact groups are for.

As standard Checkmk comes with the following three predefined roles, which can never be deleted, but can be customised at will:

When adding a new custom role, it will be a clone of one of the default roles, i.e it will automatically inherit all of the
permissions of that default role.  Also, when new permissions are added, built-in roles will automatically be permitted or not
permitted and the custom roles will also inherit those permission settings.

* Role: admin
Permissions:  All permissions - especially the right to change permissions.
Function: The Checkmk administrator who is in charge of the monitoring system itself.

* Role: user
Permissions: May only see their own hosts and services, may only make changes in the web interface in folders
authorized for them and generally may not do anything that affects other users.
Function: The normal Checkmk user who uses monitoring and responds to notifications.

* Role: guest
Permissions: May see everything but not change anything.
Function: 'Guest' is intended simply for 'watching', with all guests sharing a common account.
For example, useful for public status monitors hanging on a wall.

"""

from collections.abc import Mapping
from typing import Any

from marshmallow import ValidationError

from cmk.gui.config import active_config
from cmk.gui.fields.definitions import UserRoleID
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.user_role.request_schemas import CreateUserRole, EditUserRole
from cmk.gui.openapi.endpoints.user_role.response_schemas import UserRoleCollection, UserRoleObject
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.permissions import load_dynamic_permissions
from cmk.gui.userdb import UserRole
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.roles import get_role_permissions
from cmk.gui.watolib import userroles
from cmk.gui.watolib.userroles import RoleID

PERMISSIONS = permissions.Perm("wato.users")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


def _serialize_user_role_extensions(user_role: UserRole) -> dict[str, Any]:
    extensions = {
        "alias": user_role.alias,
        "builtin": user_role.builtin,
        "permissions": get_role_permissions().get(user_role.name),
        "enforce_two_factor_authentication": user_role.two_factor,
    }
    if not user_role.builtin:
        extensions["basedon"] = user_role.basedon
    return extensions


def serialize_user_role(user_role: UserRole) -> DomainObject:
    return constructors.domain_object(
        domain_type="user_role",
        identifier=user_role.name,
        title=user_role.alias,
        extensions=_serialize_user_role_extensions(user_role),
        editable=True,
        deletable=not user_role.builtin,
    )


@Endpoint(
    constructors.object_href("user_role", "{role_id}"),
    "cmk/show",
    method="get",
    tag_group="Setup",
    path_params=[
        {
            "role_id": UserRoleID(
                required=True,
                description="An existing user role.",
                example="userx",
                presence="should_exist",
            )
        }
    ],
    response_schema=UserRoleObject,
    permissions_required=PERMISSIONS,
)
def show_user_role(params: Mapping[str, Any]) -> Response:
    """Show a user role"""
    # TODO: clean this up (CMK-17068)
    load_dynamic_permissions()
    user.need_permission("wato.users")
    user_role = userroles.get_role(RoleID(params["role_id"]))
    return serve_json(data=serialize_user_role(user_role))


@Endpoint(
    constructors.collection_href("user_role"),
    ".../collection",
    method="get",
    tag_group="Setup",
    response_schema=UserRoleCollection,
    permissions_required=PERMISSIONS,
)
def list_user_roles(params: Mapping[str, Any]) -> Response:
    """Show all user roles"""
    # TODO: clean this up (CMK-17068)
    load_dynamic_permissions()
    user.need_permission("wato.users")

    return serve_json(
        constructors.collection_object(
            domain_type="user_role",
            value=[
                serialize_user_role(user_role) for user_role in userroles.get_all_roles().values()
            ],
        )
    )


@Endpoint(
    constructors.collection_href("user_role"),
    "cmk/create",
    method="post",
    tag_group="Setup",
    request_schema=CreateUserRole,
    response_schema=UserRoleObject,
    permissions_required=RW_PERMISSIONS,
)
def create_userrole(params: Mapping[str, Any]) -> Response:
    """Create/clone a user role"""
    # TODO: clean this up (CMK-17068) and check if this is really required.
    load_dynamic_permissions()
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    body = params["body"]
    cloned_user_role = userroles.clone_role(
        role_id=RoleID(body["role_id"]),
        new_role_id=body.get("new_role_id"),
        new_alias=body.get("new_alias"),
        two_factor=body.get("enforce_two_factor_authentication"),
        pprint_value=active_config.wato_pprint_config,
    )
    return serve_json(serialize_user_role(cloned_user_role))


@Endpoint(
    constructors.object_href("user_role", "{role_id}"),
    ".../delete",
    method="delete",
    tag_group="Setup",
    path_params=[
        {
            "role_id": UserRoleID(
                required=True,
                description="An existing custom user role that you want to delete.",
                example="userx",
                presence="should_exist",
                userrole_type="should_be_custom",
            )
        }
    ],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_userrole(params: Mapping[str, Any]) -> Response:
    """Delete a user role"""
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    role_id = RoleID(params["role_id"])
    userroles.delete_role(RoleID(role_id), pprint_value=active_config.wato_pprint_config)
    return Response(status=204)


@Endpoint(
    constructors.object_href("user_role", "{role_id}"),
    ".../update",
    method="put",
    tag_group="Setup",
    request_schema=EditUserRole,
    response_schema=UserRoleObject,
    path_params=[
        {
            "role_id": UserRoleID(
                required=True,
                description="An existing user role.",
                example="userx",
                presence="should_exist",
            )
        }
    ],
    permissions_required=RW_PERMISSIONS,
)
def edit_userrole(params: Mapping[str, Any]) -> Response:
    """Edit a user role"""
    # TODO: clean this up (CMK-17068)
    load_dynamic_permissions()
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    existing_roleid = params["role_id"]
    body = params["body"]
    userrole_to_edit: UserRole = userroles.get_role(RoleID(existing_roleid))

    if new_alias := body.get("new_alias", userrole_to_edit.alias):
        try:
            userroles.validate_new_alias(userrole_to_edit.alias, new_alias)
        except ValidationError as exc:
            return problem(status=400, title="Invalid alias", detail=str(exc))
        userrole_to_edit.alias = new_alias

    if new_roleid := body.get("new_role_id"):
        try:
            userroles.validate_new_roleid(userrole_to_edit.name, new_roleid)
        except ValidationError as exc:
            return problem(status=400, title="Invalid role id", detail=str(exc))
        userrole_to_edit.name = new_roleid

    if basedon := body.get("new_basedon"):
        if userrole_to_edit.builtin:
            return problem(
                status=400,
                title="Built-in role",
                detail="You can't edit the basedon value of a built-in role.",
            )
        userrole_to_edit.basedon = basedon

    if (two_factor := body.get("enforce_two_factor_authentication")) is not None:
        userrole_to_edit.two_factor = two_factor

    if new_permissions := body.get("new_permissions"):
        userroles.update_permissions(userrole_to_edit, new_permissions.items())

    userroles.update_role(
        role=userrole_to_edit,
        old_roleid=RoleID(existing_roleid),
        new_roleid=RoleID(userrole_to_edit.name),
        pprint_value=active_config.wato_pprint_config,
    )
    return serve_json(data=serialize_user_role(userrole_to_edit))


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_user_role, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_user_roles, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_userrole, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_userrole, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(edit_userrole, ignore_duplicates=ignore_duplicates)
