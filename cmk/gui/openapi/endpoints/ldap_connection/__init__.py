#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""LDAP Connections

Checkmk provides a facility for using LDAP-based services for managing users, automatically
synchronizing users from the home directories, and for assigning contact groups, roles and
other attributes to these users in Checkmk automatically. Checkmk is not restricted to a
single LDAP source, and it can also distribute the users to other connected sites if required.

The following endpoints provide a way to manage LDAP connections via the REST-API in the
same way the user interface does.  This includes creating, updating, deleting and listing LDAP
connections.

If you need help during configuration or experience problems, please refer to the LDAP
Documentation: https://docs.checkmk.com/latest/en/ldap.html.


"""

from collections.abc import Mapping
from typing import Any

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.custom_fields import LDAPConnectionID
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.ldap_connection.error_schemas import GETLdapConnection404
from cmk.gui.openapi.endpoints.ldap_connection.internal_to_restapi_interface import (
    LDAPConnectionInterface,
    request_ldap_connection,
    request_ldap_connections,
    request_to_create_ldap_connection,
    request_to_delete_ldap_connection,
    request_to_edit_ldap_connection,
)
from cmk.gui.openapi.endpoints.ldap_connection.request_schemas import (
    LDAPConnectionConfigCreateRequest,
    LDAPConnectionConfigUpdateRequest,
)
from cmk.gui.openapi.endpoints.ldap_connection.response_schemas import (
    LDAPConnectionResponse,
    LDAPConnectionResponseCollection,
)
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.constructors import (
    collection_href,
    collection_object,
    domain_object,
    hash_of_dict,
    object_href,
    require_etag,
    response_with_etag_created_from_dict,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions

RO_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.seeall"),
        permissions.Perm("wato.users"),
    ]
)
RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        RO_PERMISSIONS,
    ]
)


LDAP_CONNECTION_ID_EXISTS = {
    "ldap_connection_id": LDAPConnectionID(
        presence="should_exist",
        example="LDAP_1",
    ),
}


@Endpoint(
    object_href("ldap_connection", "{ldap_connection_id}"),
    "cmk/show",
    method="get",
    etag="output",
    tag_group="Setup",
    path_params=[LDAP_CONNECTION_ID_EXISTS],
    response_schema=LDAPConnectionResponse,
    error_schemas={404: GETLdapConnection404},
    permissions_required=RO_PERMISSIONS,
)
def show_ldap_connection(params: Mapping[str, Any]) -> Response:
    """Show an LDAP connection"""
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")
    ldap_id = params["ldap_connection_id"]
    connection = request_ldap_connection(ldap_id=ldap_id)
    return response_with_etag_created_from_dict(
        serve_json(
            _serialize_ldap_connection(
                request_ldap_connection(ldap_id=params["ldap_connection_id"])
            )
        ),
        connection.api_response(),
    )


@Endpoint(
    collection_href("ldap_connection"),
    ".../collection",
    method="get",
    tag_group="Setup",
    response_schema=LDAPConnectionResponseCollection,
    permissions_required=RO_PERMISSIONS,
)
def show_ldap_connections(params: Mapping[str, Any]) -> Response:
    """Show all LDAP connections"""
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")
    return serve_json(
        collection_object(
            domain_type="ldap_connection",
            value=[_serialize_ldap_connection(cnx) for cnx in request_ldap_connections().values()],
        )
    )


@Endpoint(
    object_href("ldap_connection", "{ldap_connection_id}"),
    ".../delete",
    method="delete",
    etag="input",
    path_params=[LDAP_CONNECTION_ID_EXISTS],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_ldap_connection(params: Mapping[str, Any]) -> Response:
    """Delete an LDAP connection"""
    user.need_permission("wato.edit")
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")
    ldap_id = params["ldap_connection_id"]
    if (connection := request_ldap_connection(ldap_id=ldap_id)) is not None:
        require_etag(hash_of_dict(connection.api_response()))
        request_to_delete_ldap_connection(
            params["ldap_connection_id"], pprint_value=active_config.wato_pprint_config
        )
    return Response(status=204)


@Endpoint(
    collection_href("ldap_connection"),
    "cmk/create",
    method="post",
    etag="output",
    tag_group="Setup",
    request_schema=LDAPConnectionConfigCreateRequest,
    response_schema=LDAPConnectionResponse,
    permissions_required=RW_PERMISSIONS,
)
def create_ldap_connection(params: Mapping[str, Any]) -> Response:
    """Create an LDAP connection"""
    user.need_permission("wato.edit")
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")
    connection = request_to_create_ldap_connection(
        params["body"], pprint_value=active_config.wato_pprint_config
    )
    return response_with_etag_created_from_dict(
        serve_json(_serialize_ldap_connection(connection)),
        connection.api_response(),
    )


@Endpoint(
    object_href("ldap_connection", "{ldap_connection_id}"),
    "cmk/update",
    method="put",
    etag="both",
    tag_group="Setup",
    path_params=[LDAP_CONNECTION_ID_EXISTS],
    request_schema=LDAPConnectionConfigUpdateRequest,
    response_schema=LDAPConnectionResponse,
    error_schemas={404: GETLdapConnection404},
    permissions_required=RW_PERMISSIONS,
)
def edit_ldap_connection(params: Mapping[str, Any]) -> Response:
    """Update an ldap connection"""
    user.need_permission("wato.edit")
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")
    ldap_id = params["ldap_connection_id"]
    current_connection = request_ldap_connection(ldap_id=ldap_id)
    require_etag(hash_of_dict(current_connection.api_response()))

    ldap_data = params["body"]
    ldap_data["general_properties"]["id"] = ldap_id
    try:
        updated_connection = request_to_edit_ldap_connection(
            ldap_data=ldap_data,
            ldap_id=ldap_id,
            pprint_value=active_config.wato_pprint_config,
        )
    except MKUserError as exc:
        raise ProblemException(
            title=f"There was problem when trying to update the LDAP connection with ldap_id {ldap_id}",
            detail=str(exc),
        )

    return response_with_etag_created_from_dict(
        serve_json(_serialize_ldap_connection(updated_connection)),
        updated_connection.api_response(),
    )


def _serialize_ldap_connection(connection: LDAPConnectionInterface) -> DomainObject:
    return domain_object(
        domain_type="ldap_connection",
        identifier=connection.general_properties.id,
        title=connection.general_properties.description,
        extensions=connection.api_response(),
        editable=True,
        deletable=True,
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_ldap_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_ldap_connections, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_ldap_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_ldap_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(edit_ldap_connection, ignore_duplicates=ignore_duplicates)
