#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host status

The host status provides the host's "health" information.

You can find an introduction to basic monitoring principles including host status in the
[Checkmk guide](https://docs.checkmk.com/latest/en/monitoring_basics.html).
"""

from cmk.gui import sites
from cmk.gui.plugins.openapi import fields
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
        [Column(hosts.name: string)]

        >>> p.load({})['sites']
        []

    """
    sites = fields.List(
        fields.SiteField(),
        description="Restrict the query to this particular site.",
        missing=[],
    )
    query = fields.query_field(Hosts, required=False)
    columns = fields.column_field(Hosts, mandatory=[Hosts.name])


@Endpoint(constructors.collection_href('host'),
          '.../collection',
          method='get',
          tag_group='Monitoring',
          blacklist_in=['swagger-ui'],
          query_params=[HostParameters],
          response_schema=response_schemas.DomainObjectCollection)
def list_hosts(param):
    """Show hosts of specific condition"""
    live = sites.live()
    sites_to_query = param['sites']
    if sites_to_query:
        live.only_sites = sites_to_query

    q = Query(param['columns'])

    # TODO: add sites parameter
    query_expr = param.get('query')
    if query_expr:
        q = q.filter(query_expr)

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
