#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service status

A service is a property of a certain host that is monitored by Checkmk.
A service can be almost anything - for example, a file system, a process, a hardware sensor,
a switchport - but it can also just be a specific metric like CPU usage or RAM usage.

The service status provides the service's "health" information.

You can find an introduction to services in the
[Checkmk guide](https://checkmk.com/cms_wato_services.html).
"""
import json

from cmk.gui import sites
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.endpoints.utils import verify_columns
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import tree_to_expr
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Services
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    constructors,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME

PARAMETERS = [{
    'site': fields.String(description="Restrict the query to this particular site."),
    'query': fields.Nested(
        fields.ExprSchema,
        description=("An query expression in nested dictionary form. If you want to "
                     "use multiple expressions, nest them with the AND/OR operators."),
        many=False,
        example=json.dumps({
            'op': 'not',
            'expr': {
                'op': '=',
                'left': 'hosts.name',
                'right': 'example.com'
            }
        }),
        required=False,
    ),
    'columns': fields.List(
        fields.LiveStatusColumn(
            table=Services,
            mandatory=[Services.host_name.name, Services.description.name],
        ),
        required=False,
        description="The desired columns of the services table. If left empty, a default set"
        " of columns is used.",
        missing=[
            Services.host_name.name,
            Services.description.name,
        ],
    ),
}]


@Endpoint(constructors.domain_object_sub_collection_href('host', '{host_name}', 'services'),
          '.../collection',
          method='get',
          path_params=[HOST_NAME],
          query_params=PARAMETERS,
          tag_group='Monitoring',
          response_schema=response_schemas.DomainObjectCollection)
def _list_host_services(param):
    """List a host's monitored services.

    This list is filterable by various parameters."""
    return _list_services(param)


@Endpoint(
    constructors.collection_href('service'),
    '.../collection',
    method='get',
    query_params=[HOST_NAME, *PARAMETERS],
    tag_group='Monitoring',
    response_schema=response_schemas.DomainObjectCollection,
)
def _list_all_services(param):
    """List all monitored services.

    This list is filterable by various parameters."""
    return _list_services(param)


def _list_services(param):
    live = sites.live()

    columns = verify_columns(Services, param['columns'])
    q = Query(columns)

    host_name = param.get('host_name')
    if host_name is not None:
        q = q.filter(Services.host_name == host_name)

    filter_tree = param.get('query')
    if filter_tree:
        expr = tree_to_expr(filter_tree)
        q = q.filter(expr)

    result = q.iterate(live)

    return constructors.serve_json(
        constructors.collection_object(
            domain_type='service',
            value=[
                constructors.domain_object(
                    domain_type='service',
                    title=f"{entry['description']} on {entry['host_name']}",
                    identifier=entry['description'],
                    editable=False,
                    deletable=False,
                    extensions=entry,
                ) for entry in result
            ],
        ))
