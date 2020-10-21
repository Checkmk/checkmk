#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Downtimes

A (scheduled) downtime is a planned maintenance period.
Hosts and services are handled differently by Checkmk during a downtime, for example,
notifications are disabled.

You can find an introduction to downtimes in the
[Checkmk guide](https://checkmk.com/cms_basics_downtimes.html).
"""

import json
import http.client
import datetime as dt
from typing import Dict, Literal

from cmk.gui import config, sites
from cmk.gui.http import Response
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.livestatus_helpers.commands import downtimes as downtime_commands
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import And
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables.downtimes import Downtimes
from cmk.gui.plugins.openapi.restful_objects import (
    endpoint_schema,
    request_schemas,
    constructors,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME, SERVICE_DESCRIPTION
from cmk.gui.plugins.openapi.utils import problem, ProblemException
from cmk.gui.watolib.downtime import (
    execute_livestatus_command,
    remove_downtime_command,
)

DowntimeType = Literal['host', 'service', 'hostgroup', 'servicegroup']


@endpoint_schema(constructors.collection_href('downtime'),
                 'cmk/create',
                 method='post',
                 request_schema=request_schemas.CreateDowntime,
                 output_empty=True)
def create_downtime(params):
    """Create a scheduled downtime"""
    body = params['body']
    downtime_type: DowntimeType = body['downtime_type']
    if downtime_type == 'host':
        downtime_commands.schedule_host_downtime(
            sites.live(),
            host_name=body['host_name'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', f"Downtime for host {body['host_name']!r}"),
        )
    elif downtime_type == 'hostgroup':
        downtime_commands.schedule_hostgroup_host_downtime(
            sites.live(),
            hostgroup_name=body['hostgroup_name'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', f"Downtime for hostgroup {body['hostgroup_name']!r}"),
        )
    elif downtime_type == 'service':
        downtime_commands.schedule_service_downtime(
            sites.live(),
            host_name=body['host_name'],
            service_description=body['service_descriptions'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get(
                'comment',
                f"Downtime for services {', '.join(body['service_descriptions'])!r}@{body['host_name']!r}"
            ),
        )
    elif downtime_type == 'servicegroup':
        downtime_commands.schedule_servicegroup_service_downtime(
            sites.live(),
            servicegroup_name=body['servicegroup_name'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', f"Downtime for servicegroup {body['servicegroup_name']!r}"),
        )
    else:
        return problem(status=400,
                       title="Unhandled downtime-type.",
                       detail=f"The downtime-type {downtime_type!r} is not supported.")

    return Response(status=204)


@endpoint_schema(constructors.collection_href('downtime'),
                 '.../collection',
                 method='get',
                 query_params=[
                     HOST_NAME,
                     SERVICE_DESCRIPTION,
                 ],
                 response_schema=response_schemas.DomainObjectCollection)
def list_service_downtimes(param):
    """Show all scheduled downtimes"""
    live = sites.live()

    q = Query([
        Downtimes.id,
        Downtimes.host_name,
        Downtimes.service_description,
        Downtimes.is_service,
        Downtimes.author,
        Downtimes.start_time,
        Downtimes.end_time,
        Downtimes.recurring,
        Downtimes.comment,
    ])

    host_name = param.get('host_name')
    if host_name is not None:
        q = q.filter(Downtimes.host_name.contains(host_name))

    service_description = param.get('service_description')
    if service_description is not None:
        q = q.filter(Downtimes.service_description.contains(service_description))

    gen_downtimes = q.iterate(live)
    return _serve_downtimes(gen_downtimes)


@endpoint_schema('/objects/host/{host_name}/objects/downtime/{downtime_id}',
                 '.../delete',
                 method='delete',
                 path_params=[
                     HOST_NAME,
                     {
                         'downtime_id': fields.String(
                             description='The id of the downtime',
                             example='54',
                             required=True,
                         ),
                     },
                 ],
                 output_empty=True)
def delete_downtime(params):
    """Delete a scheduled downtime"""
    is_service = Query(
        [Downtimes.is_service],
        Downtimes.id.contains(params['downtime_id']),
    ).value(sites.live())
    downtime_type = "SVC" if is_service else "HOST"
    command_delete = remove_downtime_command(downtime_type, params['downtime_id'])
    execute_livestatus_command(command_delete, params['host_name'])
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('downtime', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteDowntime,
                 output_empty=True)
def bulk_delete_downtimes(params):
    """Bulk delete downtimes"""
    live = sites.live()
    entries = params['entries']
    not_found = []

    downtimes: Dict[int, int] = Query(
        [Downtimes.id, Downtimes.is_service],
        And(*[Downtimes.id.equals(downtime_id) for downtime_id in entries]),
    ).to_dict(live)

    for downtime_id in entries:
        if downtime_id not in downtimes:
            not_found.append(downtime_id)

    if not_found:
        raise ProblemException(404, http.client.responses[400],
                               f"Downtimes {', '.join(not_found)} not found")

    for downtime_id, is_service in downtimes.items():
        if is_service:
            downtime_commands.del_service_downtime(live, downtime_id)
        else:
            downtime_commands.del_host_downtime(live, downtime_id)
    return Response(status=204)


def _serve_downtimes(downtimes):
    response = Response()
    response.set_data(json.dumps(_serialize_downtimes(downtimes)))
    response.set_content_type('application/json')
    return response


def _serialize_downtimes(downtimes):
    entries = []
    for downtime_info in downtimes:
        service_description = downtime_info.get("service_description")
        if service_description:
            downtime_detail = "service: %s" % service_description
        else:
            downtime_detail = "host: %s" % downtime_info["host_name"]

        downtime_id = downtime_info['id']
        entries.append(
            constructors.domain_object(
                domain_type='downtime',
                identifier=downtime_id,
                title='Downtime for %s' % downtime_detail,
                extensions=_downtime_properties(downtime_info),
                links=[
                    constructors.link_rel(rel='.../delete',
                                          href='/objects/host/%s/objects/downtime/%s' %
                                          (downtime_info['host_name'], downtime_id),
                                          method='delete',
                                          title='Delete the downtime'),
                ]))

    return constructors.object_collection(
        name='all',
        domain_type='downtime',
        entries=entries,
        base='',
    )


def _downtime_properties(info):
    return {
        "host_name": info['host_name'],
        "author": info['author'],
        "is_service": 'yes' if info["is_service"] else 'no',
        "start_time": _time_utc(dt.datetime.fromtimestamp(info['start_time'])),
        "end_time": _time_utc(dt.datetime.fromtimestamp(info['end_time'])),
        "recurring": 'yes' if info['recurring'] else 'no',
        "comment": info['comment']
    }


def _time_utc(time_dt):
    return time_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
