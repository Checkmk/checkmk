#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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
from collections.abc import Mapping
from typing import Any

from marshmallow.utils import from_iso_time

import cmk.utils.defines as defines
from cmk.utils.timeperiod import TimeperiodSpec

from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.endpoints.time_periods.request_schemas import (
    CreateTimePeriod,
    UpdateTimePeriod,
)
from cmk.gui.plugins.openapi.endpoints.time_periods.response_schemas import (
    TimePeriodResponse,
    TimePeriodResponseCollection,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, permissions
from cmk.gui.plugins.openapi.restful_objects.parameters import TIMEPERIOD_NAME_FIELD
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.plugins.openapi.utils import problem, ProblemException, serve_json
from cmk.gui.watolib.timeperiods import (
    delete_timeperiod,
    load_timeperiod,
    load_timeperiods,
    save_timeperiod,
    TimePeriodInUseError,
    TimePeriodNotFoundError,
)

TIME_RANGE = tuple[str, str]

PERMISSIONS = permissions.Perm("wato.timeperiods")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


def time_period_not_found_problem(time_period_id: str) -> Response:
    return problem(
        status=404,
        title="The requested time period was not found",
        detail=f"Could not find a time period with id {time_period_id}.",
    )


def _get_time_period_domain_object(
    name: str,
    api_format: dict[str, Any],
) -> DomainObject:
    return constructors.domain_object(
        domain_type="time_period",
        identifier=name,
        title=api_format["alias"],
        extensions=api_format,
        deletable=True,
        editable=True,
    )


@Endpoint(
    constructors.collection_href("time_period"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=CreateTimePeriod,
    response_schema=TimePeriodResponse,
    permissions_required=RW_PERMISSIONS,
)
def create_timeperiod(params: Mapping[str, Any]) -> Response:
    """Create a time period"""
    user.need_permission("wato.edit")
    user.need_permission("wato.timeperiods")
    body = params["body"]
    name = body["name"]
    exceptions = _format_exceptions(body.get("exceptions", []))
    periods = _daily_time_ranges(body["active_time_ranges"])
    time_period = _to_checkmk_format(
        alias=body["alias"], periods=periods, exceptions=exceptions, exclude=body.get("exclude", [])
    )
    save_timeperiod(name, time_period)
    return _serve_time_period(_get_time_period_domain_object(name, _to_api_format(time_period)))


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    ".../update",
    method="put",
    path_params=[TIMEPERIOD_NAME_FIELD],
    etag="both",
    additional_status_codes=[405],
    request_schema=UpdateTimePeriod,
    response_schema=TimePeriodResponse,
    permissions_required=RW_PERMISSIONS,
)
def update_timeperiod(params: Mapping[str, Any]) -> Response:
    """Update a time period"""
    user.need_permission("wato.edit")
    user.need_permission("wato.timeperiods")
    body = params["body"]
    name = params["name"]
    if name == "24X7":
        raise ProblemException(
            405, http.client.responses[405], "You cannot change the built-in time period"
        )
    try:
        time_period = load_timeperiod(name)
    except TimePeriodNotFoundError:
        return time_period_not_found_problem(name)

    parsed_time_period = _to_api_format(time_period, internal_format=True)

    updated_time_period = _to_checkmk_format(
        alias=body.get("alias", parsed_time_period["alias"]),
        periods=_daily_time_ranges(
            body.get("active_time_ranges", parsed_time_period["active_time_ranges"])
        ),
        exceptions=_format_exceptions(body.get("exceptions", parsed_time_period["exceptions"])),
        exclude=body.get("exclude", parsed_time_period["exclude"]),
    )
    api_format_response = _to_api_format(updated_time_period)
    save_timeperiod(name, updated_time_period)
    return _serve_time_period(_get_time_period_domain_object(name, api_format_response))


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    ".../delete",
    method="delete",
    path_params=[TIMEPERIOD_NAME_FIELD],
    etag="input",
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[409],
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a time period"""
    user.need_permission("wato.edit")
    user.need_permission("wato.timeperiods")
    name = params["name"]
    try:
        delete_timeperiod(name)
    except TimePeriodNotFoundError:
        return time_period_not_found_problem(name)
    except TimePeriodInUseError as e:
        return problem(
            status=409,
            title="The time period is still in use",
            detail=f"The time period is still in use ({', '.join(u[0] for u in e.usages)}).",
        )

    return Response(status=204)


@Endpoint(
    constructors.object_href("time_period", "{name}"),
    "cmk/show",
    method="get",
    etag="output",
    path_params=[TIMEPERIOD_NAME_FIELD],
    response_schema=TimePeriodResponse,
    permissions_required=PERMISSIONS,
)
def show_time_period(params: Mapping[str, Any]) -> Response:
    """Show a time period"""
    user.need_permission("wato.timeperiods")
    name = params["name"]

    try:
        time_period = load_timeperiod(name)
    except TimePeriodNotFoundError:
        return time_period_not_found_problem(name)

    api_format = _to_api_format(time_period, name == "24X7")
    return _serve_time_period(_get_time_period_domain_object(name, api_format))


@Endpoint(
    constructors.collection_href("time_period"),
    ".../collection",
    method="get",
    response_schema=TimePeriodResponseCollection,
    permissions_required=PERMISSIONS,
)
def list_time_periods(params: Mapping[str, Any]) -> Response:
    """Show all time periods"""
    user.need_permission("wato.timeperiods")
    return serve_json(
        constructors.collection_object(
            domain_type="time_period",
            value=[
                _get_time_period_domain_object(name, _to_api_format(time_period, name == "24X7"))
                for name, time_period in load_timeperiods().items()
            ],
        )
    )


def _serve_time_period(time_period: DomainObject) -> Response:
    response = serve_json(time_period)
    return constructors.response_with_etag_created_from_dict(response, time_period)


def _to_api_format(  # type: ignore[no-untyped-def]
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
    time_period_readable: dict[str, Any] = {"alias": time_period["alias"]}
    if not builtin_period:
        time_period_readable["exclude"] = time_period.get("exclude", [])

    active_time_ranges = _active_time_ranges_readable(
        {key: time_period[key] for key in time_period if key in defines.weekday_ids()}
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


def _daily_time_ranges(active_time_ranges: list[dict[str, Any]]) -> dict[str, list[TIME_RANGE]]:
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

    result: dict[str, list[TIME_RANGE]] = {day: [] for day in defines.weekday_ids()}
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


def _active_time_ranges_readable(days: dict[str, Any]) -> list[dict[str, Any]]:
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

    result: list[dict[str, Any]] = []
    for day, time_ranges in days.items():
        temp: list[dict[str, str]] = []
        for time_range in time_ranges:
            temp.append({"start": time_range[0], "end": time_range[1]})
        if temp:
            result.append({"day": day, "time_ranges": temp})
    return result


def _convert_to_dt(exceptions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []

    def convert_to_dt(time_range: dict[str, str]) -> dict[str, dt.time]:
        return {k: from_iso_time(v) for k, v in time_range.items()}

    for exception in exceptions:
        period = {k: v for k, v in exception.items() if k != "time_ranges"}
        period["time_ranges"] = [convert_to_dt(entry) for entry in exception["time_ranges"]]
        result.append(period)
    return result


def _format_exceptions(exceptions: list[dict[str, Any]]) -> dict[str, list[TIME_RANGE]]:
    result = {}
    for exception in exceptions:
        date_exception = []
        for time_range in exception["time_ranges"]:
            date_exception.append(_format_time_range(time_range))
        result[str(exception["date"])] = date_exception
    return result


def _exceptions_readable(mk_exceptions: dict[str, Any]) -> list[dict[str, Any]]:
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
    result: list[dict[str, Any]] = []
    for test_date, time_ranges in mk_exceptions.items():
        time_ranges_formatted: list[dict[str, str]] = []
        for time_range in time_ranges:
            time_ranges_formatted.append({"start": time_range[0], "end": time_range[1]})
        result.append({"date": test_date, "time_ranges": time_ranges_formatted})
    return result


def _time_readable(mk_time: str) -> str:
    minutes = "00" if mk_time[1] == "0" else mk_time[1]
    return f"{mk_time[0]}:{minutes}"


def _format_time_range(time_range: dict[str, dt.time]) -> TIME_RANGE:
    """Convert time iso format to Checkmk format"""
    return _mk_time_format(time_range["start"]), _mk_time_format(time_range["end"])


def _mk_time_format(time_or_str: str | dt.time) -> str:
    """

    Examples:

        >>> _mk_time_format("12:00:05")
        '12:00'

        >>> _mk_time_format("09:00:30")
        '09:00'

    """
    if isinstance(time_or_str, str):
        parts = time_or_str.split(":")
        try:
            time = dt.time(int(parts[0]), int(parts[1]))
        except ValueError:
            raise ProblemException(
                400,
                title="Invalid time format",
                detail=f"{time_or_str} is not a valid time format.",
            )
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
    periods: dict[str, Any],
    exceptions: dict[str, Any],
    exclude: list[str],
) -> TimeperiodSpec:
    time_period: dict[str, Any] = {"alias": alias}
    time_period.update(exceptions)
    time_period.update(periods)
    if exclude is None:
        exclude = []
    time_period["exclude"] = exclude
    return time_period
