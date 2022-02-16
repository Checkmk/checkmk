#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
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

For a detailed list of columns have a look at the [services table](https://github.com/tribe29/checkmk/blob/master/cmk/gui/plugins/openapi/livestatus_helpers/tables/services.py)
definition on GitHub.
"""
from cmk.utils.livestatus_helpers.expressions import And
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Services

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.plugins.openapi.restful_objects.constructors import object_action_href
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME, OPTIONAL_HOST_NAME
from cmk.gui.plugins.openapi.utils import problem

from cmk import fields

PARAMETERS = [
    {
        "sites": gui_fields.List(
            gui_fields.SiteField(),
            description="Restrict the query to this particular site.",
            load_default=list,
        ),
        "query": gui_fields.query_field(
            Services,
            required=False,
            example='{"op": "=", "left": "host_name", "right": "example.com"}',
        ),
        "columns": gui_fields.column_field(
            Services,
            mandatory=[
                Services.host_name,
                Services.description,
            ],
        ),
    }
]


@Endpoint(
    object_action_href("host", "{host_name}", "show_service"),
    "cmk/show",
    method="get",
    path_params=[HOST_NAME],
    query_params=[
        {
            "service_description": fields.String(
                description="The service description of the selected host",
                example="Filesystem %boot",
            ),
        }
    ],
    tag_group="Monitoring",
    response_schema=response_schemas.DomainObject,
)
def show_service(params):
    """Show the monitored service of a host"""
    service_description = params["service_description"]
    host_name = params["host_name"]
    live = sites.live()
    q = Query(
        [
            Services.description,
            Services.host_name,
            Services.state_type,
            Services.state,
            Services.last_check,
        ],
        filter_expr=And(
            Services.host_name.op("=", params["host_name"]),
            Services.description.op("=", service_description),
        ),
    )
    try:
        service = q.fetchone(live)
    except ValueError:
        return problem(
            status=404,
            title="The requested service was not found",
            detail=f"The service description {service_description} did not match any service",
        )
    return constructors.serve_json(
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


@Endpoint(
    constructors.domain_object_collection_href("host", "{host_name}", "services"),
    ".../collection",
    method="get",
    path_params=[HOST_NAME],
    query_params=PARAMETERS,
    tag_group="Monitoring",
    blacklist_in=["swagger-ui"],
    response_schema=response_schemas.DomainObjectCollection,
)
def _list_host_services(param):
    """Show the monitored services of a host

    This list is filterable by various parameters."""
    return _list_services(param)


@Endpoint(
    constructors.collection_href("service"),
    ".../collection",
    method="get",
    query_params=[OPTIONAL_HOST_NAME, *PARAMETERS],
    tag_group="Monitoring",
    response_schema=response_schemas.DomainObjectCollection,
)
def _list_all_services(param):
    """Show all monitored services

    This list is filterable by various parameters."""
    return _list_services(param)


def _list_services(param):
    live = sites.live()

    q = Query(param["columns"])

    host_name = param.get("host_name")
    if host_name is not None:
        q = q.filter(Services.host_name == host_name)

    query_expr = param.get("query")
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    return constructors.serve_json(
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
