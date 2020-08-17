#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service status endpoints
"""

from cmk.gui import sites
from cmk.gui.plugins.openapi.endpoints.utils import add_if_missing, verify_columns
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Services
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.plugins.openapi.restful_objects import (
    endpoint_schema,
    constructors,
    response_schemas,
    ParamDict,
)

PARAMETERS = [
    ParamDict.create(
        'host_alias',
        'query',
        example="example",
        required=False,
        schema_type='string',
    ),
    ParamDict.create(
        'acknowledged',
        'query',
        example="0",
        required=False,
        schema_type='boolean',
    ),
    ParamDict.create(
        'in_downtime',
        'query',
        example="1",
        required=False,
        schema_type='boolean',
    ),
    ParamDict.create(
        'status',
        'query',
        required=False,
        example="0",
        schema_type='integer',
        schema_num_minimum=0,
        schema_num_maximum=3,
    ),
    ParamDict.create(
        'columns',
        'query',
        required=False,
        description="The desired columns of the services table. If left empty, a default set of "
        "columns is used.",
        schema_enum=Services.__columns__(),
        schema_type='array',
    )
]


@endpoint_schema(constructors.domain_object_sub_collection_href('host', '{host_name}', 'services'),
                 '.../collection',
                 method='get',
                 parameters=[HOST_NAME] + PARAMETERS,
                 response_schema=response_schemas.DomainObjectCollection)
def _list_host_services(param):
    return _list_services(param)


@endpoint_schema(constructors.collection_href('service'),
                 '.../collection',
                 method='get',
                 parameters=[HOST_NAME(location='query', required=False)] + PARAMETERS,
                 response_schema=response_schemas.DomainObjectCollection)
def _list_all_services(param):
    return _list_services(param)


def _list_services(param):
    live = sites.live()

    default_columns = [
        'host_name',
        'description',
        'last_check',
        'state',
        'state_type',
        'acknowledged',
    ]
    column_names = add_if_missing(param.get('columns', default_columns),
                                  ['host_name', 'description'])
    columns = verify_columns(Services, column_names)
    q = Query(columns)

    host_name = param.get('host_name')
    if host_name is not None:
        q = q.filter(Services.host_name.contains(host_name))

    alias = param.get('host_alias')
    if alias is not None:
        q = q.filter(Services.host_alias.contains(alias))

    in_downtime = param.get('in_downtime')
    if in_downtime is not None:
        q = q.filter(Services.scheduled_downtime_depth == int(in_downtime))

    acknowledged = param.get('acknowledged')
    if acknowledged is not None:
        q = q.filter(Services.acknowledged.equals(acknowledged))

    status = param.get('status')
    if status is not None:
        q = q.filter(Services.state.equals(status))

    result = q.iterate(live)

    return constructors.object_collection(
        name='all',
        domain_type='service',
        entries=[
            constructors.domain_object(
                domain_type='service',
                title=f"{entry['description']} on {entry['host_name']}",
                identifier=entry['description'],
                editable=False,
                deletable=False,
                extensions=entry,
            ) for entry in result
        ],
        base='',
    )
