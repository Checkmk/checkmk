#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service status

The service status provides the service's "health" information.

A service (for example, a file system or a process) is a property of a certain host that
is monitored by Checkmk.

### Related documentation

How to use the query DSL used in the `query` parameters of these endpoints, have a look at the
[Querying Status Data](#section/Querying-Status-Data) section of this documentation.

These endpoints support all [Livestatus filter operators](https://docs.checkmk.com/latest/en/livestatus_references.html#heading_filter),
which you can look up in the Checkmk documentation.

For a detailed list of columns, have a look at the [services table](#section/Table-definitions/Services-Table) definition.
"""

from collections.abc import Mapping
from typing import Any

from cmk.utils.livestatus_helpers.expressions import And
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Services

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields import HostField
from cmk.gui.fields.base import BaseSchema
from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions

from cmk import fields


class _BaseParameters(BaseSchema):
    """Site and column parameters for the list services endpoints."""

    sites = fields.List(
        gui_fields.SiteField(),
        description="Restrict the query to this particular site.",
        load_default=[],
        example=["heute"],
    )
    columns = gui_fields.column_field(
        Services,
        mandatory=[Services.host_name, Services.description],
        example=["host_name", "description"],
    )


class ServiceParameters(_BaseParameters):
    """All the parameters for the list services endpoints."""

    query = gui_fields.query_field(
        Services,
        required=False,
        example={"op": "=", "left": "host_name", "right": "example.com"},
    )


class ServiceParametersWithHost(ServiceParameters):
    """All the parameters for the list services endpoints with optional host filter."""

    host_name = HostField(
        description="A host name.",
        should_exist=True,
        required=False,
        permission_type="monitor",
    )


PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            permissions.Perm("wato.see_all_folders"),
        ]
    )
)

QUERY_FIELD = {
    "query": gui_fields.query_field(
        Services,
        required=False,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    ),
}

HOST_NAME = {
    "host_name": HostField(
        description="A host name.",
        should_exist=True,
        permission_type="monitor",
    )
}

OPTIONAL_HOST_NAME = {
    "host_name": HostField(
        description="A host name.",
        should_exist=True,
        required=False,
        permission_type="monitor",
    )
}


@Endpoint(
    object_action_href("host", "{host_name}", "show_service"),
    "cmk/show",
    method="get",
    path_params=[HOST_NAME],
    query_params=[
        {
            "service_description": fields.String(
                description="The service name of the selected host",
                example="Filesystem /boot",
                required=True,
            ),
            "columns": gui_fields.column_field(
                Services,
                default=[
                    Services.host_name,
                    Services.description,
                    Services.state,
                    Services.state_type,
                    Services.last_check,
                ],
                example=["state", "state_type"],
            ),
        },
    ],
    tag_group="Monitoring",
    response_schema=response_schemas.DomainObject,  # TODO: response schema
    permissions_required=PERMISSIONS,
)
def show_service(params: Mapping[str, Any]) -> Response:
    """Show a single service of a specific host"""
    service_description = params["service_description"]
    host_name = params["host_name"]
    live = sites.live()
    try:
        q = Query(
            params["columns"],
            filter_expr=And(
                Services.host_name.op("=", params["host_name"]),
                Services.description.op("=", service_description),
            ),
        )
        service = q.fetchone(live)
    except ValueError:
        return problem(
            status=404,
            title="The requested service was not found",
            detail=f"The service name {service_description} did not match any service",
        )
    return serve_json(
        constructors.domain_object(
            domain_type="service",
            identifier=f"{host_name}-{service_description}",
            title=f"Service {service_description}",
            extensions=service,
            links=[],
            editable=False,
            deletable=False,
        )
    )


# TODO: DEPRECATED(17512) - remove in 2.5, still used for the "REST API exports" in the UI
@Endpoint(
    constructors.domain_object_collection_href("host", "{host_name}", "services"),
    ".../collection",
    method="get",
    path_params=[HOST_NAME],
    query_params=[_BaseParameters, QUERY_FIELD],
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    deprecated_urls={"/objects/host/{host_name}/collections/services": 17512},
)
def _list_host_services_deprecated(params: Mapping[str, Any]) -> Response:
    """Show the monitored services of a host

    This list is filterable by various parameters."""
    return _list_services(params)


@Endpoint(
    constructors.domain_object_collection_href("host", "{host_name}", "services"),
    "cmk/list",
    method="post",
    path_params=[HOST_NAME],
    tag_group="Monitoring",
    request_schema=ServiceParameters,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    update_config_generation=False,
)
def _list_host_services(params: Mapping[str, Any]) -> Response:
    """Show the monitored services of a host

    This list is filterable by various parameters."""
    # merge body and path parameters
    params["body"]["host_name"] = params["host_name"]
    return _list_services(params["body"])


# TODO: DEPRECATED(17512) - remove in 2.5, still used for the "REST API exports" in the UI
@Endpoint(
    constructors.collection_href("service"),
    ".../collection",
    method="get",
    query_params=[_BaseParameters, QUERY_FIELD, OPTIONAL_HOST_NAME],
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    deprecated_urls={"/domain-types/service/collections/all": 17512},
)
def _list_all_services_deprecated(params: Mapping[str, Any]) -> Response:
    """Show all monitored services

    This list is filterable by various parameters."""
    return _list_services(params)


@Endpoint(
    constructors.collection_href("service"),
    "cmk/list",
    method="post",
    tag_group="Monitoring",
    request_schema=ServiceParametersWithHost,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    update_config_generation=False,
)
def _list_all_services(params: Mapping[str, Any]) -> Response:
    """Show all monitored services

    This list is filterable by various parameters."""
    return _list_services(params["body"])


def _list_services(params: Mapping[str, Any]) -> Response:
    live = sites.live()
    if only_sites := params.get("sites"):
        live.set_only_sites(only_sites)

    q = Query(params["columns"])

    host_name: str | None = params.get("host_name")
    if host_name is not None:
        q = q.filter(Services.host_name == host_name)

    query_expr = params.get("query")
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    return serve_json(
        constructors.collection_object(
            domain_type="service",
            value=[
                constructors.domain_object(
                    domain_type="service",
                    title=f"{entry['description']} on {entry['host_name']}",
                    identifier=f"{entry['host_name']}:{entry['description']}",
                    editable=False,
                    deletable=False,
                    extensions=entry,
                    self_link=constructors.link_rel(
                        rel="cmk/show",
                        href=constructors.object_action_href(
                            "host",
                            entry["host_name"],
                            "show_service",
                            query_params=[("service_description", entry["description"])],
                        ),
                        method="get",
                        title=f"Show the service {entry['description']}",
                    ),
                )
                for entry in result
            ],
        )
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_service, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_list_host_services_deprecated, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_list_host_services, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_list_all_services_deprecated, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(_list_all_services, ignore_duplicates=ignore_duplicates)
