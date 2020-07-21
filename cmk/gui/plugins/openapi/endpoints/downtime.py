#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import http.client
from datetime import datetime
from typing import Dict

from connexion import ProblemException  # type: ignore[import]

from cmk.gui.http import Response
from cmk.gui import sites
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables.downtimes import Downtimes
from cmk.gui.plugins.openapi.restful_objects import ParamDict
from cmk.gui.watolib.downtime import (execute_livestatus_command, determine_downtime_mode,
                                      remove_downtime_command, DowntimeSchedule)
from cmk.gui.plugins.openapi.livestatus_helpers.commands.downtimes import (del_host_downtime,
                                                                           del_service_downtime)
from cmk.gui.plugins.openapi.restful_objects import (endpoint_schema, request_schemas, constructors,
                                                     response_schemas)

from cmk.gui.plugins.openapi.livestatus_helpers.expressions import And

RECURRING_OPTIONS = {
    "hour": 1,
    "day": 2,
    "week": 3,
    "second week": 4,
    "fourth week": 5,
    "same weekday": 6,
    "same day of the month": 7
}

DOWNTIME_ID = ParamDict.create('downtime_id',
                               'path',
                               description='The id of the downtime',
                               example='54',
                               required=True)


@endpoint_schema(constructors.collection_href('downtime'),
                 'cmk/create',
                 method='post',
                 request_schema=request_schemas.CreateDowntime,
                 output_empty=True)
def create_downtime(params):
    body = params['body']
    host_name = body['host_name']
    start_dt = _time_dt(body['start_time'])
    end_dt = _time_dt(body['end_time'])
    delayed_duration = body.get("delayed_duration", 0)
    if "recurring_option" not in body:
        recurring_number = 0
    else:
        recurring_number = RECURRING_OPTIONS[body["recurring_option"]]
    mode = determine_downtime_mode(recurring_number, delayed_duration)

    if "service_description" in body:
        service_description = body["service_description"]
        spec = _service_spec(service_description, host_name)
        comment = body.get("comment", "Downtime for service: %s" % service_description)
        downtime_tag = "SVC"
    else:
        spec = host_name
        downtime_tag = "HOST"
        comment = body.get("comment", "Downtime for host: %s" % host_name)
    downtime = DowntimeSchedule(start_dt.timestamp(), end_dt.timestamp(), mode, delayed_duration,
                                comment)
    command = downtime.livestatus_command(spec, downtime_tag)
    execute_livestatus_command(command, host_name)
    return Response(status=204)


@endpoint_schema(constructors.collection_href('downtime'),
                 '.../collection',
                 method='get',
                 parameters=[
                     ParamDict.create('host_name', 'query', required=False,
                                      schema_type='string').to_dict(),
                     ParamDict.create('service_description',
                                      'query',
                                      required=False,
                                      schema_type='string').to_dict()
                 ],
                 response_schema=response_schemas.DomainObjectCollection)
def list_service_downtimes(param):
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
                 parameters=['host_name', DOWNTIME_ID],
                 output_empty=True)
def delete_downtime(params):
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
    """Bulk delete downtimes based upon downtime id"""
    live = sites.live()
    entries = params['entries']
    not_found = []

    downtimes: Dict[str, int] = {
        downtime_id: is_service for downtime_id, is_service in Query(  # pylint: disable=unnecessary-comprehension
            [Downtimes.id, Downtimes.is_service],
            And(*[Downtimes.id.equals(downtime_id) for downtime_id in entries]),
        ).fetch_values(live)
    }

    for downtime_id in entries:
        if downtime_id not in downtimes:
            not_found.append(downtime_id)

    if not_found:
        raise ProblemException(404, http.client.responses[400],
                               f"Downtimes {', '.join(not_found)} not found")

    for downtime_id, is_service in downtimes.items():
        if is_service:
            del_service_downtime(live, downtime_id)
        else:
            del_host_downtime(live, downtime_id)
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
        "start_time": _time_utc(datetime.fromtimestamp(info['start_time'])),
        "end_time": _time_utc(datetime.fromtimestamp(info['end_time'])),
        "recurring": 'yes' if info['recurring'] else 'no',
        "comment": info['comment']
    }


def _service_spec(service_description, host_name):
    return "%s;%s" % (service_description, host_name)


def _time_dt(time_str):
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S%z")


def _time_utc(time_dt):
    return time_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
