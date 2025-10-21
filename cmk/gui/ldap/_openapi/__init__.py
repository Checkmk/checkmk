#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""LDAP Connections

# mypy: disable-error-code="comparison-overlap"

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
from cmk.gui.i18n import _
from cmk.gui.ldap._openapi.error_schemas import GETLdapConnection404
from cmk.gui.ldap._openapi.internal_to_restapi_interface import (
    LDAPConnectionInterface,
    request_ldap_connection,
    request_ldap_connections,
    update_suffixes,
)
from cmk.gui.ldap._openapi.request_schemas import (
    LDAPConnectionConfigCreateRequest,
    LDAPConnectionConfigUpdateRequest,
)
from cmk.gui.ldap._openapi.response_schemas import (
    LDAPConnectionResponse,
    LDAPConnectionResponseCollection,
)
from cmk.gui.logged_in import user
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
from cmk.gui.user_connection_config_types import LDAPUserConnectionConfig, SAMLUserConnectionConfig
from cmk.gui.userdb import get_ldap_connections, UserConnectionConfigFile
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.wato.pages.userdb_common import get_affected_sites
from cmk.gui.watolib.config_domains import ConfigDomainGUI

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

        config_file = UserConnectionConfigFile()
        all_connections = config_file.load_for_modification()
        updated_connections = [c for c in all_connections if c["id"] != ldap_id]
        deleted_connection = [c for c in all_connections if c["id"] == ldap_id][0]
        update_suffixes(updated_connections)
        config_file.delete(
            user_id=user.id,
            cfg=updated_connections,
            connection_id=ldap_id,
            connection_type="ldap",
            sites=get_affected_sites(active_config.sites, deleted_connection),
            domains=[ConfigDomainGUI()],
            pprint_value=active_config.wato_pprint_config,
            use_git=active_config.wato_use_git,
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

    connection = LDAPConnectionInterface.from_api_request(params["body"])
    config_file = UserConnectionConfigFile()
    all_connections = config_file.load_for_modification()
    all_connections.append(connection.to_mk_format())
    update_suffixes(all_connections)

    config_file.create(
        user_id=user.id,
        cfg=all_connections,
        connection_type="ldap",
        sites=get_affected_sites(active_config.sites, connection.to_mk_format()),
        domains=[ConfigDomainGUI()],
        pprint_value=active_config.wato_pprint_config,
        use_git=active_config.wato_use_git,
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
        if ldap_data["ldap_connection"]["connection_suffix"]["state"] == "enabled":
            for ldap_connection in [
                cnx for ldapid, cnx in get_ldap_connections().items() if ldapid != ldap_id
            ]:
                if (suffix := ldap_connection.get("suffix")) is not None:
                    if suffix == ldap_data["ldap_connection"]["connection_suffix"]["suffix"]:
                        raise MKUserError(
                            None,
                            _("The suffix '%s' is already in use by another LDAP connection.")
                            % ldap_connection["suffix"],
                        )

        config_file = UserConnectionConfigFile()
        ldap_connection_from_request = LDAPConnectionInterface.from_api_request(ldap_data)
        updated_connection = ldap_connection_from_request.to_mk_format()

        modified_connections: list[LDAPUserConnectionConfig | SAMLUserConnectionConfig] = [
            updated_connection if connection["id"] == ldap_id else connection
            for connection in config_file.load_for_modification()
        ]

        update_suffixes(modified_connections)

        config_file.update(
            user_id=user.id,
            cfg=modified_connections,
            connection_id=ldap_id,
            connection_type="ldap",
            sites=get_affected_sites(active_config.sites, updated_connection),
            domains=[ConfigDomainGUI()],
            pprint_value=active_config.wato_pprint_config,
            use_git=active_config.wato_use_git,
        )

    except MKUserError as exc:
        raise ProblemException(
            title=f"There was problem when trying to update the LDAP connection with ldap_id {ldap_id}",
            detail=str(exc),
        )

    return response_with_etag_created_from_dict(
        serve_json(_serialize_ldap_connection(ldap_connection_from_request)),
        ldap_connection_from_request.api_response(),
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
