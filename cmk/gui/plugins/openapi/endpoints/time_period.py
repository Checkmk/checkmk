#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Time periods"""

import http.client
import datetime as dt
import json

from typing import List, Dict, Any, Tuple

from connexion import ProblemException  # type: ignore[import]

from cmk.utils.type_defs import TimeperiodSpec
from cmk.gui.http import Response

import cmk.utils.defines as defines
from cmk.gui.watolib.timeperiods import save_timeperiod, load_timeperiod, load_timeperiods, save_timeperiods
from cmk.gui.plugins.openapi.restful_objects import (
    endpoint_schema,
    request_schemas,
    response_schemas,
    constructors,
)

TIME = Tuple[str, str]
TIME_RANGE = Tuple[TIME, TIME]


@endpoint_schema(constructors.collection_href('time_period'),
                 'cmk/create',
                 method='post',
                 request_schema=request_schemas.InputTimePeriod,
                 output_empty=True)
def create_timeperiod(params):
    """Create a time period"""
    body = params['body']
    exceptions = _format_exceptions(body.get("exceptions", []))
    periods = _daily_time_ranges(body["active_time_ranges"])
    time_period = _time_period(alias=body['alias'],
                               periods=periods,
                               exceptions=exceptions,
                               exclude=body.get("exclude", []))
    save_timeperiod(body['name'], time_period)
    return Response(status=204)


@endpoint_schema(constructors.object_href('time_period', '{name}'),
                 '.../update',
                 method='put',
                 parameters=['name'],
                 request_schema=request_schemas.UpdateTimePeriod,
                 output_empty=True)
def update_timeperiod(params):
    """Update a time period"""

    body = params['body']
    name = params['name']
    time_period = load_timeperiod(name)
    if time_period is None:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")

    if "exceptions" in body:
        time_period = dict((key, time_period[key])
                           for key in [*defines.weekday_ids(), "alias", "exclude"]
                           if key in time_period)
        time_period["exceptions"] = _format_exceptions(body["exceptions"])

    if "alias" in body:
        time_period['alias'] = body['alias']

    if "active_time_ranges" in body:
        time_period.update(_daily_time_ranges(body['active_time_ranges']))

    if "exclude" in body:
        time_period["exclude"] = body["exclude"]

    save_timeperiod(name, time_period)
    return Response(status=204)


@endpoint_schema(constructors.object_href('time_period', '{name}'),
                 '.../delete',
                 method='delete',
                 parameters=['name'],
                 request_body_required=False,
                 output_empty=True)
def delete(params):
    """Delete a time period"""
    name = params['name']
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")
    del time_periods[name]
    save_timeperiods(time_periods)
    return Response(status=204)


@endpoint_schema(constructors.object_href('time_period', '{name}'),
                 'cmk/show',
                 method='get',
                 parameters=['name'],
                 response_schema=response_schemas.ConcreteTimePeriod)
def show_time_period(params):
    """Show a time period"""
    name = params['name']
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")
    time_period = time_periods[name]

    time_period_readable: Dict[str, Any] = {key: time_period[key] for key in ("alias", "exclude")}
    active_time_ranges = _active_time_ranges_readable(
        {key: time_period[key] for key in defines.weekday_ids()})
    time_period_readable["active_time_ranges"] = active_time_ranges
    time_period_readable["exceptions"] = _exceptions_readable({
        key: time_period[key]
        for key in time_period
        if key not in ['alias', 'exclude', *defines.weekday_ids()]
    })
    return _serve_time_period(time_period_readable)


def _serve_time_period(time_period):
    response = Response()
    response.set_data(json.dumps(time_period))
    response.set_content_type('application/json')
    return response


def _daily_time_ranges(active_time_ranges: List[Dict[str, Any]]) -> Dict[str, List[TIME_RANGE]]:
    """Convert the user provided time ranges to the Checkmk format

    Args:
        active_time_ranges:
            The list of specific time ranges

    Returns:
        A dict which contains the week days as keys and their associating time ranges as values

    Examples:
        >>> _daily_time_ranges(
        ... [{"day": "monday", "time_ranges": [{"start": dt.time(12), "end": dt.time(14)}]}])
        {'monday': [(('12', '0'), ('14', '0'))], \
'tuesday': [], 'wednesday': [], 'thursday': [], 'friday': [], 'saturday': [], 'sunday': []}
    """

    result: Dict[str, List[TIME_RANGE]] = {day: [] for day in defines.weekday_ids()}
    for active_time_range in active_time_ranges:
        period = active_time_range["day"]  # weekday or week
        time_ranges = [
            _format_time_range(time_range) for time_range in active_time_range["time_ranges"]
        ]
        if period == "all":
            for day_time_ranges in result.values():
                day_time_ranges.extend(time_ranges)
        else:  # specific day
            result[period].extend(time_ranges)
    return result


def _active_time_ranges_readable(days: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert the Checkmk time ranges to the API format

    Args:
        days:
            The dict which contains the week days as keys and their associating times ranges as values

    Returns:
        A list of dicts where each dict represents a daily time range

    Examples:
        >>> _active_time_ranges_readable(
        ... {'monday': [(('12', '0'), ('14', '0'))], 'tuesday': [], 'wednesday': [],
        ... 'thursday': [], 'friday': [], 'saturday': [], 'sunday': []})
        [{'day': 'monday', 'time_ranges': [{'start': '12:00', 'end': '14:00'}]}]
    """

    result: List[Dict[str, Any]] = []
    for day, time_ranges in days.items():
        temp: List[Dict[str, str]] = []
        for time_range in time_ranges:
            temp.append({
                "start": _time_readable(time_range[0]),
                "end": _time_readable(time_range[1])
            })
        if temp:
            result.append({"day": day, "time_ranges": temp})
    return result


def _format_exceptions(exceptions: List[Dict[str, Any]]) -> Dict[str, List[TIME_RANGE]]:
    result = {}
    for exception in exceptions:
        date_exception = []
        for time_range in exception["time_ranges"]:
            date_exception.append(_format_time_range(time_range))
        result[str(exception['date'])] = date_exception
    return result


def _exceptions_readable(mk_exceptions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert the Checkmk exceptions to the API exception format

    Args:
        mk_exceptions:
            Dict where keys are the exception dates and values are their associating time ranges

    Returns:
        A list containing the formatted exceptions

    Examples:
        >>> _exceptions_readable({"2020-01-01": [(('14', '0'), ('18', '0'))]})
        [{'date': '2020-01-01', 'time_ranges': [{'start': '14:00', 'end': '18:00'}]}]

    """
    result: List[Dict[str, Any]] = []
    for test_date, time_ranges in mk_exceptions.items():
        time_ranges_formatted: List[Dict[str, str]] = []
        for time_range in time_ranges:
            time_ranges_formatted.append({
                "start": _time_readable(time_range[0]),
                "end": _time_readable(time_range[1])
            })
        result.append({"date": test_date, "time_ranges": time_ranges_formatted})
    return result


def _time_readable(mk_time: TIME) -> str:
    minutes = "00" if mk_time[1] == "0" else mk_time[1]
    return f"{mk_time[0]}:{minutes}"


def _format_time_range(time_range: Dict[str, dt.time]) -> TIME_RANGE:
    """Convert time iso format to Checkmk format"""
    return _mk_time_format(time_range['start']), _mk_time_format(time_range['end'])


def _mk_time_format(time: dt.time) -> TIME:
    minutes = time.strftime("%M")
    minutes = "0" if minutes == "00" else minutes
    return time.strftime("%H"), minutes


def _mk_date_format(exception_date: dt.date) -> str:
    return exception_date.strftime("%Y-%m-%d")


def _time_period(
    alias: str,
    periods: Dict[str, Any],
    exceptions: Dict[str, Any],
    exclude: List[str],
) -> TimeperiodSpec:
    time_period: Dict[str, Any] = {"alias": alias}
    time_period.update(exceptions)
    time_period.update(periods)
    if exclude is None:
        exclude = []
    time_period["exclude"] = exclude
    return time_period
