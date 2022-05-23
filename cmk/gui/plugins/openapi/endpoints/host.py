#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host status

The host status provides the host's "health" information.

### Related documentation

How to use the query DSL used in the `query` parameters of these endpoints, have a look at the
[Querying Status Data](#section/Querying-Status-Data) section of this documentation.

These endpoints support all [Livestatus filter operators](https://docs.checkmk.com/latest/en/livestatus_references.html#heading_filter),
which you can look up in the Checkmk documentation.

For a detailed list of columns, please take a look at the [hosts table](https://github.com/tribe29/checkmk/blob/master/cmk/gui/plugins/openapi/livestatus_helpers/tables/hosts.py)
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
from cmk.utils.livestatus_helpers.queries import Query
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

    q = Query(param["columns"])

    query_expr = param.get("query")
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    return constructors.serve_json(
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
