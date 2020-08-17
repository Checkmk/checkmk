#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host status endpoints
"""

from cmk.gui import sites
from cmk.gui.plugins.openapi.endpoints.utils import add_if_missing, verify_columns
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Hosts
from cmk.gui.plugins.openapi.restful_objects import (
    endpoint_schema,
    constructors,
    response_schemas,
    ParamDict,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME


@endpoint_schema(constructors.collection_href('host'),
                 '.../collection',
                 method='get',
                 parameters=[
                     HOST_NAME(
                         location='query',
                         required=False,
                         description=Hosts.name.__doc__,
                     ),
                     ParamDict.create(
                         'host_alias',
                         'query',
                         required=False,
                         description=Hosts.alias.__doc__,
                         schema_type='string',
                     ),
                     ParamDict.create(
                         'acknowledged',
                         'query',
                         required=False,
                         example='1',
                         description=Hosts.acknowledged.__doc__,
                         schema_type='boolean',
                     ),
                     ParamDict.create(
                         'in_downtime',
                         'query',
                         required=False,
                         example="0",
                         description="Whether the host is currently in a downtime (0/1)",
                         schema_type='boolean',
                     ),
                     ParamDict.create(
                         'status',
                         'query',
                         required=False,
                         description=Hosts.state.__doc__,
                         schema_type='integer',
                         schema_num_minimum=0,
                         schema_num_maximum=3,
                     ),
                     ParamDict.create(
                         'columns',
                         'query',
                         required=False,
                         description="The desired columns of the hosts table. If left empty, "
                         "a default set of columns is used.",
                         schema_enum=Hosts.__columns__(),
                         schema_type='array',
                     )
                 ],
                 response_schema=response_schemas.DomainObjectCollection)
def list_hosts(param):
    """List currently monitored hosts."""
    live = sites.live()

    default_columns = [
        'name',
        'address',
        'alias',
        'downtimes_with_info',
        'scheduled_downtime_depth',
    ]
    column_names = add_if_missing(param.get('columns', default_columns), ['name', 'address'])
    columns = verify_columns(Hosts, column_names)
    q = Query(columns)

    host_name = param.get('host_name')
    if host_name is not None:
        q = q.filter(Hosts.name.contains(host_name))

    host_alias = param.get('host_alias')
    if host_alias is not None:
        q = q.filter(Hosts.alias.contains(host_alias))

    in_downtime = param.get('in_downtime')
    if in_downtime is not None:
        q = q.filter(Hosts.scheduled_downtime_depth == int(in_downtime))

    acknowledged = param.get('acknowledged')
    if acknowledged is not None:
        q = q.filter(Hosts.acknowledged.equals(acknowledged))

    status = param.get('status')
    if status is not None:
        q = q.filter(Hosts.state.equals(status))

    result = q.iterate(live)

    return constructors.object_collection(
        name='all',
        domain_type='host',
        entries=[
            constructors.domain_object(
                domain_type='host',
                title=f"{entry['name']} ({entry['address']})",
                identifier=entry['name'],
                editable=False,
                deletable=False,
                extensions=entry,
            ) for entry in result
        ],
        base='',
    )
