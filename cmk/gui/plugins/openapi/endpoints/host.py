#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host status

The host status provides the host's "health" information.

You can find an introduction to basic monitoring principles including host status in the
[Checkmk guide](https://checkmk.com/cms_monitoring_basics.html).
"""

import json

from cmk.gui import sites
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.endpoints.utils import verify_columns
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import tree_to_expr
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Hosts
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    constructors,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import BaseSchema


class HostParameters(BaseSchema):
    """All the parameters for the hosts list.

    Examples:

        >>> p = HostParameters()
        >>> p.load({})['columns']
        ['name']

        >>> p.load({})['sites']
        []

    """
    sites = fields.List(
        fields.String(),
        description="Restrict the query to this particular site.",
        missing=[],
    )
    query = fields.Nested(
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
    )
    columns = fields.List(
        fields.LiveStatusColumn(
            table=Hosts,
            mandatory=[Hosts.name.name],
            required=True,
        ),
        description=("The desired columns of the hosts table. If left empty, a default set of "
                     "columns is used."),
        missing=[Hosts.name.name],
        required=False,
    )


@Endpoint(constructors.collection_href('host'),
          '.../collection',
          method='get',
          tag_group='Monitoring',
          query_params=[HostParameters],
          response_schema=response_schemas.DomainObjectCollection)
def list_hosts(param):
    """Show hosts of specific condition"""
    live = sites.live()
    sites_to_query = param['sites']
    if sites_to_query:
        live.only_sites = sites_to_query

    columns = verify_columns(Hosts, param['columns'])
    q = Query(columns)

    # TODO: add sites parameter
    filter_tree = param.get('query')
    if filter_tree:
        expr = tree_to_expr(filter_tree)
        q = q.filter(expr)

    result = q.iterate(live)

    return constructors.serve_json(
        constructors.collection_object(
            domain_type='host',
            value=[
                constructors.domain_object(
                    domain_type='host',
                    title=f"{entry['name']}",
                    identifier=entry['name'],
                    editable=False,
                    deletable=False,
                    extensions=entry,
                ) for entry in result
            ],
        ))
