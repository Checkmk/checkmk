#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import datetime

from cmk.gui.http import Response
from cmk.gui.watolib.downtime import (execute_livestatus_command, determine_downtime_mode,
                                      DowntimeSchedule)
from cmk.gui.plugins.openapi.restful_objects import (endpoint_schema, request_schemas, constructors)

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


def _service_spec(service_description, host_name):
    return "%s;%s" % (service_description, host_name)


def _time_dt(time_str):
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S%z")
