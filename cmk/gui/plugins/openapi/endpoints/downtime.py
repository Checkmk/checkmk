#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from datetime import datetime

from cmk.gui.http import Response
from cmk.gui import sites
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables.downtimes import Downtimes
from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict
from cmk.gui.watolib.downtime import (execute_livestatus_command, determine_downtime_mode,
                                      DowntimeSchedule)
from cmk.gui.plugins.openapi.restful_objects import (endpoint_schema, request_schemas, constructors,
                                                     response_schemas)

RECURRING_OPTIONS = {
    "hour": 1,
    "day": 2,
    "week": 3,
    "second week": 4,
    "fourth week": 5,
    "same weekday": 6,
    "same day of the month": 7
}


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


def _serve_downtimes(downtimes):
    response = Response()
    response.set_data(json.dumps(serialize_downtimes(downtimes)))
    response.set_content_type('application/json')
    return response


def serialize_downtimes(downtimes):
    entries = []
    for downtime_info in downtimes:
        service_description = downtime_info.get("service_description")
        if service_description:
            downtime_detail = "service: %s" % service_description
        else:
            downtime_detail = "host: %s" % downtime_info["host_name"]

        entries.append(
            constructors.domain_object(
                domain_type='downtime',
                identifier=downtime_info['id'],
                title='Downtime for %s' % downtime_detail,
                extensions=_downtime_properties(downtime_info),
            ))

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
