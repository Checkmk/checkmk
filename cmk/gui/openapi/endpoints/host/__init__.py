#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host status

The host status provides the host's "health" information.

### Related documentation

How to use the query DSL used in the `query` parameters of these endpoints, have a look at the
[Querying Status Data](#section/Querying-Status-Data) section of this documentation.

These endpoints support all [Livestatus filter operators](https://docs.checkmk.com/latest/en/livestatus_references.html#heading_filter),
which you can look up in the Checkmk documentation.

For a detailed list of columns, please take a look at the [hosts table](#section/Table-definitions/Hosts-Table) definition.

### Examples

The query expression for all non-OK hosts would be:

    {'op': '!=', 'left': 'state', 'right': '0'}

To search for unreachable hosts:

    {'op': '=', 'left': 'state', 'right': '2'}

To search for all hosts with their host name or alias starting with 'location1-':

    {'op': '~', 'left': 'name', 'right': 'location1-.*'}

    {'op': '~', 'left': 'alias', 'right': 'location1-.*'}

To search for hosts with specific tags set on them:

    {'op': '~', 'left': 'tag_names', 'right': 'windows'}

"""

import ast
from collections.abc import Generator, Mapping, Sequence
from typing import Any

from cmk.utils.livestatus_helpers.queries import Query, ResultRow
from cmk.utils.livestatus_helpers.tables import Hosts

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions

from cmk import fields


class HostParameters(BaseSchema):
    """All the parameters for the hosts list.

    Examples:

        >>> p = HostParameters()
        >>> p.load({})['columns']
        [Column(hosts.name: string)]

        >>> p.load({})['sites']
        []

    """

    sites = fields.List(
        gui_fields.SiteField(),
        description="Restrict the query to this particular site.",
        load_default=[],
        example=["heute"],
    )
    query = gui_fields.query_field(Hosts, required=False)
    columns = gui_fields.column_field(Hosts, mandatory=[Hosts.name], example=["name"])


class SingleHostParameters(BaseSchema):
    columns = gui_fields.column_field(
        Hosts, mandatory=[Hosts.name], example=["name"], required=False
    )


PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    )
)


def _list_hosts(params: Mapping[str, Any]) -> Response:
    live = sites.live()
    sites_to_query = params["sites"]
    if sites_to_query:
        live.only_sites = sites_to_query

    columns = params["columns"]
    q = Query(columns)

    query_expr = params.get("query")
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    # We have to special case the inventory column, as it is a dict stored as bytes in livestatus
    if contains_inventory_column(columns):
        result = fixup_inventory_column(result)

    return serve_json(
        constructors.collection_object(
            domain_type="host",
            value=[_host_object(entry["name"], entry) for entry in result],
        )
    )


# TODO: DEPRECATED(17003) - remove in 2.5, still used for the "REST API exports" in the UI
@Endpoint(
    constructors.collection_href("host"),
    ".../collection",
    method="get",
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    query_params=[HostParameters],
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    deprecated_urls={"/domain-types/host/collections/all": 17003},
)
def list_hosts_deprecated(params: Mapping[str, Any]) -> Response:
    """Show hosts of specific condition"""
    return _list_hosts(params)


@Endpoint(
    constructors.collection_href("host"),
    "cmk/list",
    method="post",
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    request_schema=HostParameters,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
    update_config_generation=False,
)
def list_hosts(params: Mapping[str, Any]) -> Response:
    """Show hosts of specific condition"""
    return _list_hosts(params["body"])


@Endpoint(
    constructors.object_href("host", "{host_name}"),
    "cmk/show",
    method="get",
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="The host name",
                should_exist=None,
                example="example.com",
                required=True,
            ),
        }
    ],
    query_params=[SingleHostParameters],
    response_schema=response_schemas.DomainObject,
    permissions_required=PERMISSIONS,
)
def show_host(params: Mapping[str, Any]) -> Response:
    """Show host"""
    live = sites.live()
    host_name = params["host_name"]

    q = Query(
        columns=params.get("columns", [Hosts.name, Hosts.alias, Hosts.address]),
        filter_expr=Hosts.name.op("=", host_name),
    )

    try:
        host = q.fetchone(live)
    except ValueError:
        return problem(
            status=404,
            title="The requested host was not found",
            detail=f"The host name {host_name} did not match any host",
        )
    return serve_json(_host_object(host_name, host))


def _host_object(host_name: str, host: dict) -> DomainObject:
    return constructors.domain_object(
        domain_type="host",
        identifier=host_name,
        title=host_name,
        extensions=host,
        editable=False,
        deletable=False,
    )


INVENTORY_COLUMN = "mk_inventory"


def contains_inventory_column(columns: Sequence[str]) -> bool:
    return INVENTORY_COLUMN in columns


def fixup_inventory_column(
    result: Generator[ResultRow, None, None],
) -> Generator[ResultRow, None, None]:
    for row in result:
        if inventory_data := row.get(INVENTORY_COLUMN):
            copy = dict(row)
            copy[INVENTORY_COLUMN] = ast.literal_eval(inventory_data.decode("utf-8"))
            yield ResultRow(copy)
        else:
            yield row


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(list_hosts_deprecated, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_hosts, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_host, ignore_duplicates=ignore_duplicates)
