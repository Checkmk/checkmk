#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

For a detailed list of columns, please take a look at the [hosts table](https://github.com/checkmk/checkmk/blob/master/cmk/gui/plugins/openapi/livestatus_helpers/tables/hosts.py)
definition on GitHub.

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
from typing import Generator, Sequence

from cmk.utils.livestatus_helpers.queries import Query, ResultRow
from cmk.utils.livestatus_helpers.tables import Hosts

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import serve_json

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
    )
    query = gui_fields.query_field(Hosts, required=False)
    columns = gui_fields.column_field(Hosts, mandatory=[Hosts.name], example=["name"])


PERMISSIONS = permissions.Ignore(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.Perm("bi.see_all"),
            permissions.Perm("mkeventd.seeall"),
        ]
    )
)


@Endpoint(
    constructors.collection_href("host"),
    ".../collection",
    method="get",
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    query_params=[HostParameters],
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
)
def list_hosts(param):
    """Show hosts of specific condition"""
    live = sites.live()
    sites_to_query = param["sites"]
    if sites_to_query:
        live.only_sites = sites_to_query

    columns = param["columns"]
    q = Query(columns)

    query_expr = param.get("query")
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    # We have to special case the inventory column, as they as dicts stored as bytes in livestatus
    if contains_an_inventory_colum(columns):
        result = fixup_inventory_column(result)

    return serve_json(
        constructors.collection_object(
            domain_type="host",
            value=[
                constructors.domain_object(
                    domain_type="host",
                    title=f"{entry['name']}",
                    identifier=entry["name"],
                    editable=False,
                    deletable=False,
                    extensions=entry,
                )
                for entry in result
            ],
        )
    )


INVENTORY_COLUMN = "mk_inventory"


def contains_an_inventory_colum(columns: Sequence[str]) -> bool:
    return INVENTORY_COLUMN in columns


def fixup_inventory_column(
    result: Generator[ResultRow, None, None]
) -> Generator[ResultRow, None, None]:
    for row in result:
        if (inventory_data := row.get(INVENTORY_COLUMN)) is not None:
            copy = dict(row)
            copy[INVENTORY_COLUMN] = ast.literal_eval(inventory_data.decode("utf-8"))
            yield ResultRow(copy)
        else:
            yield row
