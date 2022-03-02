#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Time periods

With time periods the monitoring with Checkmk can be adapted to recurring conditions, for
example, to avoid senseless notifications.

You can find an introduction to time periods in the
[Checkmk guide](https://docs.checkmk.com/latest/en/timeperiods.html).
"""

import datetime as dt
import http.client
import json
from typing import Any, Dict, List, Tuple, Union

from marshmallow.utils import from_iso_time

import cmk.utils.defines as defines
from cmk.utils.type_defs import TimeperiodSpec

from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.plugins.openapi.utils import ProblemException
from cmk.gui.watolib.timeperiods import (
    load_timeperiod,
    load_timeperiods,
    save_timeperiod,
    save_timeperiods,
)

TIME_RANGE = Tuple[str, str]


@Endpoint(
    constructors.collection_href("time_period"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.InputTimePeriod,
    response_schema=response_schemas.DomainObject,
)
def create_timeperiod(params):
    """Create a time period"""
    body = params["body"]
    name = body["name"]
    exceptions = _format_exceptions(body.get("exceptions", []))
    periods = _daily_time_ranges(body["active_time_ranges"])
    time_period = _to_checkmk_format(
        alias=body["alias"], periods=periods, exceptions=exceptions, exclude=body.get("exclude", [])
    )
    save_timeperiod(name, time_period)
    return _serve_time_period(_to_api_format(load_timeperiod(name)))


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    ".../update",
    method="put",
    path_params=[NAME_FIELD],
    additional_status_codes=[405],
    request_schema=request_schemas.UpdateTimePeriod,
    output_empty=True,
)
def update_timeperiod(params):
    """Update a time period"""

    body = params["body"]
    name = params["name"]
    if name == "24X7":
        raise ProblemException(
            405, http.client.responses[405], "You cannot change the built-in time period"
        )
    try:
        time_period = load_timeperiod(name)
    except KeyError:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")

    time_period = _to_api_format(time_period, internal_format=True)

    updated_time_period = _to_checkmk_format(
        alias=body.get("alias", time_period["alias"]),
        periods=_daily_time_ranges(
            body.get("active_time_ranges", time_period["active_time_ranges"])
        ),
        exceptions=_format_exceptions(body.get("exceptions", time_period["exceptions"])),
        exclude=body.get("exclude", time_period["exclude"]),
    )

    save_timeperiod(name, updated_time_period)
    return Response(status=204)


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_FIELD],
    etag="input",
    output_empty=True,
)
def delete(params):
    """Delete a time period"""
    name = params["name"]
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")
    del time_periods[name]
    save_timeperiods(time_periods)
    return Response(status=204)


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    "cmk/show",
    method="get",
    path_params=[NAME_FIELD],
    response_schema=response_schemas.ConcreteTimePeriod,
)
def show_time_period(params):
    """Show a time period"""
    name = params["name"]
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise ProblemException(404, http.client.responses[404], f"Time period {name} not found")
    time_period = time_periods[name]
    return _serve_time_period(_to_api_format(time_period, name == "24X7"))


@Endpoint(
    constructors.collection_href("time_period"),
    ".../collection",
    method="get",
    response_schema=response_schemas.DomainObjectCollection,
)
def list_time_periods(params):
    """Show all time periods"""
    time_periods = []
    for time_period_id, time_period_details in load_timeperiods().items():
        alias = time_period_details["alias"]
        if not isinstance(alias, str):  # check for mypy
            continue
        time_periods.append(
            constructors.collection_item(
                domain_type="time_period",
                title=alias,
                identifier=time_period_id,
            )
        )
    time_period_collection = {
        "id": "timeperiod",
        "domainType": "time_period",
        "value": time_periods,
        "links": [constructors.link_rel("self", constructors.collection_href("time_period"))],
    }
    return constructors.serve_json(time_period_collection)


def _serve_time_period(time_period):
    response = Response()
    response.set_data(json.dumps(time_period))
    response.set_content_type("application/json")
    response.headers.add("ETag", constructors.etag_of_dict(time_period).to_header())
    return response


def _to_api_format(
    time_period: TimeperiodSpec, builtin_period: bool = False, internal_format: bool = False
):
    """Convert time_period to API format as specified in request schema

    Args:
        time_period:
            time period which has the internal checkmk format
        builtin_period:
            bool specifying if the time period is a built-in time period
        internal_format:
            bool which determines if the time ranges should be compatible for internal processing

    Examples:
        >>> _to_api_format({'alias': 'Test All days 8x5', '2021-04-01': [('14:00', '15:00')],
        ... 'monday': [('08:00', '12:30'), ('13:30', '17:00')], 'tuesday': [], 'wednesday': [],
        ... 'thursday': [], 'friday': [], 'saturday': [], 'sunday': [], 'exclude': []})
        {'alias': 'Test All days 8x5', 'exclude': [], 'active_time_ranges': \
[{'day': 'monday', 'time_ranges': [{'start': '08:00', 'end': '12:30'}, {'start': '13:30', \
'end': '17:00'}]}], 'exceptions': [{'date': '2021-04-01', 'time_ranges': [{'start': '14:00', 'end': '15:00'}]}]}

    """
    time_period_readable: Dict[str, Any] = {"alias": time_period["alias"]}
    if not builtin_period:
        time_period_readable["exclude"] = time_period.get("exclude", [])

    active_time_ranges = _active_time_ranges_readable(
        {key: time_period[key] for key in defines.weekday_ids()}
    )
    exceptions = _exceptions_readable(
        {
            key: time_period[key]
            for key in time_period
            if key not in ["alias", "exclude", *defines.weekday_ids()]
        }
    )

    if internal_format:
        active_time_ranges = _convert_to_dt(active_time_ranges)
        exceptions = _convert_to_dt(exceptions)

    time_period_readable["active_time_ranges"] = active_time_ranges
    time_period_readable["exceptions"] = exceptions
    return time_period_readable


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
        {'monday': [('12:00', '14:00')], 'tuesday': [], 'wednesday': [], 'thursday': [], \
'friday': [], 'saturday': [], 'sunday': []}

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
        [{'day': 'monday', 'time_ranges': [{'start': ('12', '0'), 'end': ('14', '0')}]}]
    """

    result: List[Dict[str, Any]] = []
    for day, time_ranges in days.items():
        temp: List[Dict[str, str]] = []
        for time_range in time_ranges:
            temp.append({"start": time_range[0], "end": time_range[1]})
        if temp:
            result.append({"day": day, "time_ranges": temp})
    return result


def _convert_to_dt(exceptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []

    def convert_to_dt(time_range: Dict[str, str]) -> Dict[str, dt.time]:
        return {k: from_iso_time(v) for k, v in time_range.items()}

    for exception in exceptions:
        period = {k: v for k, v in exception.items() if k != "time_ranges"}
        period["time_ranges"] = [convert_to_dt(entry) for entry in exception["time_ranges"]]
        result.append(period)
    return result


def _format_exceptions(exceptions: List[Dict[str, Any]]) -> Dict[str, List[TIME_RANGE]]:
    result = {}
    for exception in exceptions:
        date_exception = []
        for time_range in exception["time_ranges"]:
            date_exception.append(_format_time_range(time_range))
        result[str(exception["date"])] = date_exception
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
        [{'date': '2020-01-01', 'time_ranges': [{'start': ('14', '0'), 'end': ('18', '0')}]}]

    """
    result: List[Dict[str, Any]] = []
    for test_date, time_ranges in mk_exceptions.items():
        time_ranges_formatted: List[Dict[str, str]] = []
        for time_range in time_ranges:
            time_ranges_formatted.append({"start": time_range[0], "end": time_range[1]})
        result.append({"date": test_date, "time_ranges": time_ranges_formatted})
    return result


def _time_readable(mk_time: str) -> str:
    minutes = "00" if mk_time[1] == "0" else mk_time[1]
    return f"{mk_time[0]}:{minutes}"


def _format_time_range(time_range: Dict[str, dt.time]) -> TIME_RANGE:
    """Convert time iso format to Checkmk format"""
    return _mk_time_format(time_range["start"]), _mk_time_format(time_range["end"])


def _mk_time_format(time_or_str: Union[str, dt.time]) -> str:
    """

    Examples:

        >>> _mk_time_format("12:00:05")
        '12:00'

        >>> _mk_time_format("09:00:30")
        '09:00'

    """
    if isinstance(time_or_str, str):
        parts = time_or_str.split(":")
        time = dt.time(int(parts[0]), int(parts[1]))
    elif isinstance(time_or_str, dt.time):
        time = time_or_str
    else:
        raise NotImplementedError()
    return f"{time.hour:02d}:{time.minute:02d}"


def _mk_date_format(exception_date: dt.date) -> str:
    """

    Examples:

        >>> _mk_date_format(dt.date(2021, 12, 21))
        '2021-12-21'

        >>> _mk_date_format(dt.date(2021, 1, 1))
        '2021-01-01'

    """
    return exception_date.strftime("%Y-%m-%d")


def _to_checkmk_format(
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
