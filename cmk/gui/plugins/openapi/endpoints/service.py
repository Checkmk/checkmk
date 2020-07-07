#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui import sites
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Services
from cmk.gui.plugins.openapi.restful_objects import endpoint_schema, constructors, response_schemas
from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict


@endpoint_schema(constructors.collection_href('service'),
                 '.../collection',
                 method='get',
                 parameters=[
                     ParamDict.create(
                         'host_name',
                         'query',
                         required=False,
                         schema_type='string',
                     ).to_dict(),
                     ParamDict.create(
                         'host_alias',
                         'query',
                         required=False,
                         schema_type='string',
                     ).to_dict(),
                     ParamDict.create(
                         'acknowledged',
                         'query',
                         required=False,
                         schema_type='boolean',
                     ).to_dict(),
                     ParamDict.create(
                         'in_downtime',
                         'query',
                         required=False,
                         schema_type='boolean',
                     ).to_dict(),
                     ParamDict.create(
                         'status',
                         'query',
                         required=False,
                         schema_type='integer',
                         schema_num_minimum=0,
                         schema_num_maximum=3,
                     ).to_dict(),
                 ],
                 response_schema=response_schemas.DomainObjectCollection)
def list_services(param):
    live = sites.live()

    q = Query([
        Services.host_name,
        Services.description,
        Services.last_check,
        Services.state,
    ])

    hostname = param.get('host_name')
    if hostname is not None:
        q = q.filter(Services.host_name.contains(hostname))

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
            ) for entry in result
        ],
        base='',
    )
