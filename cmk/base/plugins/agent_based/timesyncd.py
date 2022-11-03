#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple, TypedDict

import pytz
from dateutil import parser as date_parser
from typing_extensions import NotRequired

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.timesync import tolerance_check


class CheckParams(TypedDict):
    stratum_level: int
    quality_levels: Tuple[float, float]
    alert_delay: Tuple[int, int]
    last_synchronized: NotRequired[Tuple[int, int]]
    last_ntp_message: Tuple[int, int]


default_check_parameters = CheckParams(
    stratum_level=10,
    quality_levels=(200.0, 500.0),
    alert_delay=(300, 3600),
    last_ntp_message=(3600, 7200),
)


@dataclass(frozen=True)
class _TimeUnit:
    text_representations: Sequence[str]
    multiple_of_seconds: float


_UNITS_TO_SECONDS = {
    unit: time_unit.multiple_of_seconds
    for time_unit in [
        _TimeUnit(["y", "year", "years"], 31557600),
        _TimeUnit(["M", "month, months"], 2630016),
        _TimeUnit(["w", "week", "weeks"], 604800),
        _TimeUnit(["d", "day", "days"], 86400),
        _TimeUnit(["h", "hour", "hours"], 3600),
        _TimeUnit(["m", "min", "minute", "minutes"], 60),
        _TimeUnit(["s", "sec", "second", "seconds"], 1),
        _TimeUnit(["msec", "ms"], 1e-3),
        _TimeUnit(["µs", "usec", "us"], 1e-6),
    ]
    for unit in time_unit.text_representations
}


class Section(TypedDict, total=False):
    synctime: float
    server: str
    stratum: int
    offset: float
    jitter: float


@dataclass(frozen=True)
class NTPMessageSection:
    receivetimestamp: float


def _strip_sign(time_string: str) -> Tuple[str, int]:
    if time_string[0] == "-":
        return time_string[1:], -1
    if time_string[0] == "+":
        return time_string[1:], 1

    return time_string, 1


def _split_into_components(time_string: str) -> Iterable[float]:
    if time_string[-1].isdigit():  # 3h18 -> 3h18s
        time_string += "s"

    split_at_numbers = re.split("([0-9]*[.]?[0-9]+)", time_string)[1:]
    for value_str, unit in zip(split_at_numbers[::2], split_at_numbers[1::2]):
        yield float(value_str) * _UNITS_TO_SECONDS[unit]


def _get_seconds(time_components: Iterable[str]) -> float:
    """
    Convert a systemd time span to seconds.

    See systemd.time(7) for a detailed description of the format.

    >>> _get_seconds(["1h30m2s90us"])
    5402.00009
    >>> _get_seconds(["-2h15"])
    -7215.0
    >>> _get_seconds(["-2y","5M","2w","8d","9h","1min","53.991us"])
    -78198540.00005399
    """
    time_string = "".join(time_components)
    time_string, sign = _strip_sign(time_string)
    return sign * sum(_split_into_components(time_string))  # type: ignore


def parse_timesyncd(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if not line:
            continue

        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            section["synctime"] = float(line[0][3:-3])
            continue

        key = line[0].replace(":", "").lower()

        if key == "server":
            section["server"] = line[1].replace("(", "").replace(")", "")
        if key == "stratum":
            section["stratum"] = int(line[1])
        if key == "offset":
            section["offset"] = _get_seconds(line[1:])
        if key == "jitter":
            section["jitter"] = _get_seconds(line[1:])

    return section


def _parse_ntp_message_timestamp(ntp_message_raw: str, timezone_raw: str) -> float:
    ntp_message = ntp_message_raw.removeprefix("NTPMessage={ ").removesuffix(" }")
    ntp_message_parsed = dict((m.split("=", maxsplit=1) for m in ntp_message.split(", ")))

    receive_timestamp_raw = ntp_message_parsed["ReceiveTimestamp"]
    tz_info = pytz.timezone(timezone_raw.removeprefix("Timezone="))
    receive_datetime = date_parser.parse(receive_timestamp_raw)
    if receive_datetime.tzinfo is None:  # parsing e.g. "CEST" does not always work
        receive_datetime = tz_info.localize(receive_datetime)

    receive_timestamp = receive_datetime.astimezone(pytz.utc).timestamp()
    return receive_timestamp


def parse_timesyncd_ntpmessage(string_table: StringTable) -> Optional[NTPMessageSection]:
    if not string_table:
        return None
    ntp_message_lines = [line[0] for line in string_table if line[0].startswith("NTPMessage")]
    if len(ntp_message_lines) == 0:
        return None
    [ntp_message_line] = ntp_message_lines
    [timezone_line] = [line[0] for line in string_table if line[0].startswith("Timezone")]
    section = NTPMessageSection(
        receivetimestamp=_parse_ntp_message_timestamp(ntp_message_line, timezone_line)
    )
    return section


def _get_levels_seconds(params: Mapping[str, Any]) -> Tuple[float, float]:
    warn_milli, crit_milli = params["quality_levels"]
    return warn_milli / 1000.0, crit_milli / 1000.0


def discover_timesyncd(
    section_timesyncd: Optional[Section],
    section_timesyncd_ntpmessage: Optional[NTPMessageSection],
) -> DiscoveryResult:
    if section_timesyncd:
        yield Service()


def check_timesyncd(
    params: Mapping[str, Any],
    section_timesyncd: Optional[Section],
    section_timesyncd_ntpmessage: Optional[NTPMessageSection],
) -> CheckResult:
    if section_timesyncd is None:
        return

    levels = _get_levels_seconds(params)

    # Offset information
    offset = section_timesyncd.get("offset")
    if offset is not None:
        yield from check_levels(
            value=abs(offset),
            metric_name="time_offset",
            levels_upper=levels,
            render_func=render.timespan,
            label="Offset",
        )

    synctime = section_timesyncd.get("synctime")
    levels_upper = (
        params.get("alert_delay") if synctime is None else params.get("last_synchronized")
    )
    yield from tolerance_check(
        sync_time=synctime,
        levels_upper=levels_upper,
        value_store=get_value_store(),
        metric_name="last_sync_time",
        label="Time since last sync",
        value_store_key="time_server",
    )

    if section_timesyncd_ntpmessage is not None:
        yield from tolerance_check(
            sync_time=section_timesyncd_ntpmessage.receivetimestamp,
            levels_upper=params.get("last_ntp_message"),
            value_store=get_value_store(),
            metric_name="last_sync_receive_time",
            label="Time since last NTPMessage",
            value_store_key="last_sync_receive_time",
        )

    server = section_timesyncd.get("server")
    if server is None or server == "null":
        yield Result(state=State.CRIT, summary="Found no time server")
        return

    if (stratum := section_timesyncd.get("stratum")) is not None:
        yield from check_levels(
            value=stratum,
            levels_upper=(stratum_level := params["stratum_level"] - 1, stratum_level),
            label="Stratum",
        )

    # Jitter Information append
    jitter = section_timesyncd.get("jitter")
    if jitter is not None:
        yield from check_levels(
            value=jitter,
            metric_name="jitter",
            levels_upper=levels,
            render_func=render.timespan,
            label="Jitter",
        )

    # server is configured and can be resolved, but e.g. NTP blocked by firewall
    if server is not None and all(item is None for item in [offset, stratum, jitter]):
        yield Result(state=State.CRIT, summary="Found no time server")
        return

    yield Result(state=State.OK, summary="Synchronized on %s" % server)


register.agent_section(
    name="timesyncd",
    parse_function=parse_timesyncd,
)
register.agent_section(
    name="timesyncd_ntpmessage",
    parse_function=parse_timesyncd_ntpmessage,
)
register.check_plugin(
    name="timesyncd",
    service_name="Systemd Timesyncd Time",
    sections=["timesyncd", "timesyncd_ntpmessage"],
    discovery_function=discover_timesyncd,
    check_function=check_timesyncd,
    check_default_parameters=default_check_parameters,
    check_ruleset_name="timesyncd_time",
)
