#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Broker Connection

The broker connection endpoints give you the flexibility to configure peer to
peer broker connections with distributed sites the same way you would via the web interface.

The broker connection endpoints allow for:

* LIST for getting the list of broker connections.
* GET for getting a broker connection.
* POST for creating a new broker connection.
* PUT for updating an existing broker connection.
* DELETE for deleting an existing broker connection.

"""

from collections.abc import Mapping
from typing import Any

from livestatus import BrokerConnections, ConnectionId

from cmk.ccc.site import SiteId

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.definitions import ConnectionIdentifier
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.broker_connection.request_schemas import (
    BrokerConnectionRequestCreate,
    BrokerConnectionRequestUpdate,
)
from cmk.gui.openapi.endpoints.broker_connection.response_schemas import (
    BrokerConnectionResponse,
    BrokerConnectionResponseCollection,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.constructors import (
    domain_object,
    response_with_etag_created_from_dict,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.broker_connections import (
    BrokerConnectionConfig,
    BrokerConnectionInfo,
    SiteConnectionInfo,
)
from cmk.gui.watolib.site_management import (
    add_changes_after_editing_broker_connection,
    SitesApiMgr,
)

PERMISSIONS = permissions.Perm("wato.sites")


CONNECTION_ID_SHOULD_EXIST = {
    "connection_id": ConnectionIdentifier(
        required=True,
        presence="should_exist",
        description="An unique connection id for the broker connection",
        example="connection_1",
    )
}


def _validation_error(exc: MKUserError) -> Response:
    return problem(
        status=400,
        title="Initiating and accepting peer are already connected",
        detail=str(exc),
    )


def _serialize_broker_connection(
    connection: BrokerConnectionConfig, *, include_extensions: bool = True
) -> DomainObject:
    return domain_object(
        domain_type="broker_connection",
        identifier=connection.connection_id,
        title=f"Description of site connection id: {connection.connection_id}",
        extensions=dict(connection.to_external()) if include_extensions else None,
        editable=True,
        deletable=True,
    )


@Endpoint(
    constructors.collection_href("broker_connection"),
    ".../collection",
    method="get",
    tag_group="Checkmk Internal",
    response_schema=BrokerConnectionResponseCollection,
    permissions_required=PERMISSIONS,
)
def show_broker_connections(params: Mapping[str, Any]) -> Response:
    """Show all peer to peer broker connections"""
    user.need_permission("wato.sites")
    all_connections: BrokerConnections = SitesApiMgr().get_broker_connections()
    all_connections_objs: list[BrokerConnectionConfig] = [
        BrokerConnectionConfig.from_internal(connection_id, connection)
        for connection_id, connection in all_connections.items()
    ]

    return serve_json(
        constructors.collection_object(
            domain_type="broker_connection",
            value=[_serialize_broker_connection(connection) for connection in all_connections_objs],
        )
    )


@Endpoint(
    constructors.object_href("broker_connection", "{connection_id}"),
    "cmk/show",
    method="get",
    tag_group="Checkmk Internal",
    path_params=[CONNECTION_ID_SHOULD_EXIST],
    response_schema=BrokerConnectionResponse,
    permissions_required=PERMISSIONS,
    etag="output",
)
def show_broker_connection(params: Mapping[str, Any]) -> Response:
    """Show a peer to peer broker connection"""
    user.need_permission("wato.sites")
    connection_obj = _get_broker_connection(params["connection_id"])
    response = serve_json(data=_serialize_broker_connection(connection_obj))
    return response_with_etag_created_from_dict(response, connection_obj.to_external())


def _get_broker_connection(connection_id: str) -> BrokerConnectionConfig:
    all_connections: BrokerConnections = SitesApiMgr().get_broker_connections()
    connection = all_connections[ConnectionId(connection_id)]
    return BrokerConnectionConfig.from_internal(ConnectionId(connection_id), connection)


def _validate_and_save_boker_connection(
    connection_id_request: str,
    connection_request: dict[str, dict[str, SiteId]],
    *,
    is_new_connection: bool,
    pprint_value: bool,
) -> BrokerConnectionConfig:
    connection_info = BrokerConnectionInfo(
        connecter=SiteConnectionInfo(site_id=connection_request["connecter"]["site_id"]),
        connectee=SiteConnectionInfo(site_id=connection_request["connectee"]["site_id"]),
    )

    connection_obj = BrokerConnectionConfig.from_external(connection_id_request, connection_info)
    internal_config = connection_obj.to_internal()
    site_to_update = SitesApiMgr().validate_and_save_broker_connection(
        ConnectionId(connection_id_request),
        internal_config,
        is_new=is_new_connection,
        pprint_value=pprint_value,
    )

    add_changes_after_editing_broker_connection(
        connection_id=connection_id_request,
        is_new_broker_connection=is_new_connection,
        sites=list(site_to_update),
    )

    return connection_obj


@Endpoint(
    constructors.collection_href("broker_connection"),
    "cmk/create",
    method="post",
    tag_group="Checkmk Internal",
    response_schema=BrokerConnectionResponse,
    request_schema=BrokerConnectionRequestCreate,
    permissions_required=PERMISSIONS,
    etag="output",
)
def create_broker_connection(params: Mapping[str, Any]) -> Response:
    """Create a peer to peer broker connection"""
    user.need_permission("wato.sites")

    connection_id_request = params["body"]["connection_id"]
    connection_request = params["body"]["connection_config"]
    try:
        connection_obj = _validate_and_save_boker_connection(
            connection_id_request=connection_id_request,
            connection_request=connection_request,
            is_new_connection=True,
            pprint_value=active_config.wato_pprint_config,
        )
    except MKUserError as exc:
        return _validation_error(exc)

    response = serve_json(data=_serialize_broker_connection(connection_obj))
    return response_with_etag_created_from_dict(response, connection_obj.to_external())


@Endpoint(
    constructors.object_href("broker_connection", "{connection_id}"),
    "cmk/update",
    method="put",
    tag_group="Checkmk Internal",
    path_params=[CONNECTION_ID_SHOULD_EXIST],
    response_schema=BrokerConnectionResponse,
    request_schema=BrokerConnectionRequestUpdate,
    permissions_required=PERMISSIONS,
    etag="both",
)
def edit_broker_connection(params: Mapping[str, Any]) -> Response:
    """Edit a peer to peer broker connection"""
    user.need_permission("wato.sites")

    connection_id_request = params["connection_id"]
    connection_request = params["body"]["connection_config"]
    constructors.require_etag(
        constructors.hash_of_dict(_get_broker_connection(connection_id_request).to_external())
    )

    try:
        connection_obj = _validate_and_save_boker_connection(
            connection_id_request=connection_id_request,
            connection_request=connection_request,
            is_new_connection=False,
            pprint_value=active_config.wato_pprint_config,
        )
    except MKUserError as exc:
        return _validation_error(exc)

    response = serve_json(data=_serialize_broker_connection(connection_obj))
    return response_with_etag_created_from_dict(response, connection_obj.to_external())


@Endpoint(
    constructors.object_href("broker_connection", "{connection_id}"),
    ".../delete",
    method="delete",
    tag_group="Checkmk Internal",
    path_params=[CONNECTION_ID_SHOULD_EXIST],
    output_empty=True,
    permissions_required=PERMISSIONS,
)
def delete_broker_connection(params: Mapping[str, Any]) -> Response:
    """Delete a peer to peer broker connection"""
    user.need_permission("wato.sites")

    connection_id_request = params["connection_id"]

    site_to_update = SitesApiMgr().delete_broker_connection(
        connection_id_request,
        pprint_value=active_config.wato_pprint_config,
    )
    add_changes_after_editing_broker_connection(
        connection_id=connection_id_request,
        is_new_broker_connection=False,
        sites=list(site_to_update),
    )

    return Response(status=204)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_broker_connections, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_broker_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_broker_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(edit_broker_connection, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_broker_connection, ignore_duplicates=ignore_duplicates)
