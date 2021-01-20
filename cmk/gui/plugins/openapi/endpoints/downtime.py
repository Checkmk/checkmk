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
[Checkmk guide](https://docs.checkmk.com/latest/en/basics_downtimes.html).
"""

import json
import datetime as dt
from typing import Literal

from cmk.gui import config, sites
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.livestatus_helpers.commands import downtimes as downtime_commands
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import tree_to_expr
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables.downtimes import Downtimes
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    request_schemas,
    constructors,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME, SERVICE_DESCRIPTION, QUERY
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.plugins.openapi.utils import BaseSchema

DowntimeType = Literal['host', 'service', 'hostgroup', 'servicegroup', 'host_by_query',
                       'service_by_query']


class DowntimeParameter(BaseSchema):
    query = QUERY


@Endpoint(constructors.collection_href('downtime', 'host'),
          'cmk/create_host',
          method='post',
          tag_group='Monitoring',
          request_schema=request_schemas.CreateHostRelatedDowntime,
          output_empty=True)
def create_host_related_downtime(params):
    """Create a host related scheduled downtime"""
    body = params['body']
    live = sites.live()

    downtime_type: DowntimeType = body['downtime_type']

    if downtime_type == 'host':
        downtime_commands.schedule_host_downtime(
            live,
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
            live,
            hostgroup_name=body['hostgroup_name'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', f"Downtime for hostgroup {body['hostgroup_name']!r}"),
        )

    elif downtime_type == 'host_by_query':
        downtime_commands.schedule_hosts_downtimes_with_query(
            live,
            body['query'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', ''),
        )
    else:
        return problem(status=400,
                       title="Unhandled downtime-type.",
                       detail=f"The downtime-type {downtime_type!r} is not supported.")

    return Response(status=204)


@Endpoint(constructors.collection_href('downtime', 'service'),
          'cmk/create_service',
          method='post',
          tag_group='Monitoring',
          request_schema=request_schemas.CreateServiceRelatedDowntime,
          output_empty=True)
def create_service_related_downtime(params):
    """Create a service related scheduled downtime"""
    body = params['body']
    live = sites.live()

    downtime_type: DowntimeType = body['downtime_type']

    if downtime_type == 'service':
        downtime_commands.schedule_service_downtime(
            live,
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
            live,
            servicegroup_name=body['servicegroup_name'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', f"Downtime for servicegroup {body['servicegroup_name']!r}"),
        )
    elif downtime_type == 'service_by_query':
        downtime_commands.schedule_services_downtimes_with_query(
            live,
            query=body['query'],
            start_time=body['start_time'],
            end_time=body['end_time'],
            recur=body['recur'],
            duration=body['duration'],
            user_id=config.user.ident,
            comment=body.get('comment', ''),
        )
    else:
        return problem(status=400,
                       title="Unhandled downtime-type.",
                       detail=f"The downtime-type {downtime_type!r} is not supported.")

    return Response(status=204)


@Endpoint(constructors.collection_href('downtime'),
          '.../collection',
          method='get',
          tag_group='Monitoring',
          query_params=[
              HOST_NAME,
              SERVICE_DESCRIPTION,
              DowntimeParameter,
          ],
          response_schema=response_schemas.DomainObjectCollection)
def show_downtimes(param):
    """Show all scheduled downtimes"""
    live = sites.live()
    sites_to_query = param.get('sites')
    if sites_to_query:
        live.only_sites = sites_to_query

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

    filter_tree = param.get('query')
    host_name = param.get('host_name')
    service_description = param.get('service_description')
    if filter_tree is not None:
        expr = tree_to_expr(filter_tree, Downtimes.__tablename__)
        q = q.filter(expr)

    if host_name is not None:
        q = q.filter(Downtimes.host_name.contains(host_name))

    if service_description is not None:
        q = q.filter(Downtimes.service_description.contains(service_description))

    gen_downtimes = q.iterate(live)
    return _serve_downtimes(gen_downtimes)


@Endpoint(constructors.domain_type_action_href('downtime', 'delete'),
          '.../delete',
          method='post',
          tag_group='Monitoring',
          request_schema=request_schemas.DeleteDowntime,
          output_empty=True)
def delete_downtime(params):
    """Delete a scheduled downtime"""
    body = params['body']
    live = sites.live()
    delete_type = body['delete_type']
    if delete_type == "query":
        downtime_commands.delete_downtime_with_query(live, body['query'])
    elif delete_type == "params":
        downtime_commands.delete_downtime(live, body['downtime_id'])
    else:
        return problem(status=400,
                       title="Unhandled delete_type.",
                       detail=f"The downtime-type {delete_type!r} is not supported.")
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
