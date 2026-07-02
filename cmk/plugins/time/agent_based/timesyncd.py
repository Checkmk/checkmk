#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"

# Example output from agent:
# <<<timesyncd>>>
#        Server: 185.125.190.58 (ntp.ubuntu.com)
# Poll interval: 34min 8s (min: 32s; max 34min 8s)
#          Leap: normal
#       Version: 4
#       Stratum: 2
#     Reference: 63DC0885
#     Precision: 1us (-25)
# Root distance: 2.937ms (max: 5s)
#        Offset: +16.781ms
#         Delay: 52.183ms
#        Jitter: 52.340ms
#  Packet count: 50
#     Frequency: -2.764ppm
# [[[1783588479]]]
# <<<timesyncd_ntpmessage:sep(10)>>>
# NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-25, RootDelay=5.264ms,
#     RootDispersion=305us, Reference=63DC0885,
#     OriginateTimestamp=Thu 2026-07-09 11:14:39 CEST, ReceiveTimestamp=Thu 2026-07-09 11:14:39 CEST,
#     TransmitTimestamp=Thu 2026-07-09 11:14:39 CEST, DestinationTimestamp=Thu 2026-07-09 11:14:39 CEST,
#     Ignored=no, PacketCount=50, Jitter=52.340ms }
# Timezone=Europe/Berlin

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from dateutil import parser as date_parser
from dateutil import tz

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_value_store,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.timesync import tolerance_check


class CheckParams(TypedDict):
    stratum_level: NoLevelsT | FixedLevelsT[int]
    quality_levels: NoLevelsT | FixedLevelsT[float]
    jitter_levels: NoLevelsT | FixedLevelsT[float]
    alert_delay: NoLevelsT | FixedLevelsT[float]
    last_synchronized: NotRequired[NoLevelsT | FixedLevelsT[float]]
    last_ntp_message: NoLevelsT | FixedLevelsT[float]


default_check_parameters = CheckParams(
    stratum_level=("fixed", (10, 16)),
    quality_levels=("fixed", (0.2, 0.5)),
    jitter_levels=("no_levels", None),
    alert_delay=("fixed", (300.0, 3600.0)),
    last_ntp_message=("fixed", (3600.0, 7200.0)),
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
    server_name: str
    stratum: int
    offset: float
    jitter: float


@dataclass(frozen=True)
class NTPMessageSection:
    receivetimestamp: float


def _strip_sign(time_string: str) -> tuple[str, int]:
    match time_string[0]:  # type: ignore[exhaustive-match]
        case "-":
            return time_string[1:], -1
        case "+":
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
    return sign * sum(_split_into_components(time_string))


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
            # timedatectl prints "Server: <address> (<name>)". The address is
            # "(null)" when it could not be resolved; the name may be absent.
            section["server"] = line[1].strip("()")
            if len(line) > 2:
                section["server_name"] = " ".join(line[2:]).strip("()")
        if key == "stratum":
            section["stratum"] = int(line[1])
        if key == "offset":
            section["offset"] = _get_seconds(line[1:])
        if key == "jitter":
            section["jitter"] = _get_seconds(line[1:])

    return section


def _parse_ntp_message_timestamp(ntp_message_raw: str, timezone_raw: str) -> float:
    ntp_message = ntp_message_raw.removeprefix("NTPMessage={ ").removesuffix(" }")
    ntp_message_parsed = dict(m.split("=", maxsplit=1) for m in ntp_message.split(", "))

    receive_timestamp_raw = ntp_message_parsed["ReceiveTimestamp"]
    tz_abbr = receive_timestamp_raw.split(" ")[-1]
    tz_iana_id = timezone_raw.removeprefix("Timezone=")
    receive_datetime = date_parser.parse(
        receive_timestamp_raw, tzinfos={tz_abbr: tz.gettz(tz_iana_id)}
    )

    return receive_datetime.timestamp()


def parse_timesyncd_ntpmessage(string_table: StringTable) -> NTPMessageSection | None:
    if not string_table:
        return None
    ntp_message_lines = [line[0] for line in string_table if line[0].startswith("NTPMessage")]
    if len(ntp_message_lines) == 0:
        return None
    [ntp_message_line] = ntp_message_lines
    timezone_lines = [line[0] for line in string_table if line[0].startswith("Timezone")]
    if len(timezone_lines) == 0:
        return None
    [timezone_line] = timezone_lines
    return NTPMessageSection(
        receivetimestamp=_parse_ntp_message_timestamp(ntp_message_line, timezone_line)
    )


def _fixed_levels(levels: NoLevelsT | FixedLevelsT[float] | None) -> tuple[float, float] | None:
    # tolerance_check (shared with the ntp check) still expects a bare (warn, crit) tuple.
    match levels:
        case ("fixed", (warn, crit)):
            return warn, crit
        case _:
            return None


def _render_server(address: str, name: str | None) -> str:
    if name and name != address:
        return f"{address} ({name})"
    return address


def discover_timesyncd(
    section_timesyncd: Section | None,
    section_timesyncd_ntpmessage: NTPMessageSection | None,  # noqa: ARG001
) -> DiscoveryResult:
    if section_timesyncd:
        yield Service()


def check_timesyncd(
    params: CheckParams,
    section_timesyncd: Section | None,
    section_timesyncd_ntpmessage: NTPMessageSection | None,
) -> CheckResult:
    if section_timesyncd is None:
        return

    # Offset information
    offset = section_timesyncd.get("offset")
    if offset is not None:
        yield from check_levels(
            value=abs(offset),
            metric_name="time_offset",
            levels_upper=params["quality_levels"],
            render_func=render.timespan,
            label="Offset",
        )

    synctime = section_timesyncd.get("synctime")
    levels_upper = params["alert_delay"] if synctime is None else params.get("last_synchronized")
    yield from tolerance_check(
        sync_time=synctime,
        levels_upper=_fixed_levels(levels_upper),
        value_store=get_value_store(),
        metric_name="last_sync_time",
        label="Time since last sync",
        value_store_key="time_server",
    )

    if section_timesyncd_ntpmessage is not None:
        yield from tolerance_check(
            sync_time=section_timesyncd_ntpmessage.receivetimestamp,
            levels_upper=_fixed_levels(params["last_ntp_message"]),
            value_store=get_value_store(),
            metric_name="last_sync_receive_time",
            label="Time since last NTPMessage",
            value_store_key="last_sync_receive_time",
            notice_only=True,
        )

    server = section_timesyncd.get("server")
    if server is None or server == "null":
        yield Result(state=State.CRIT, summary="Found no time server")
        return

    if (stratum := section_timesyncd.get("stratum")) is not None:
        yield from check_levels(
            value=stratum,
            levels_upper=params["stratum_level"],
            render_func=lambda v: f"{v:.0f}",
            label="Stratum",
        )

    # Jitter Information append
    jitter = section_timesyncd.get("jitter")
    if jitter is not None:
        yield from check_levels(
            value=jitter,
            metric_name="jitter",
            levels_upper=params["jitter_levels"],
            render_func=render.timespan,
            label="Jitter",
        )

    # server is configured and can be resolved, but e.g. NTP blocked by firewall
    if server is not None and all(item is None for item in [offset, stratum, jitter]):  # type: ignore[redundant-expr]
        yield Result(state=State.CRIT, summary="Found no time server")
        return

    yield Result(
        state=State.OK,
        notice="Synchronized on %s" % _render_server(server, section_timesyncd.get("server_name")),
    )


agent_section_timesyncd = AgentSection(
    name="timesyncd",
    parse_function=parse_timesyncd,
)
agent_section_timesyncd_ntpmessage = AgentSection(
    name="timesyncd_ntpmessage",
    parse_function=parse_timesyncd_ntpmessage,
)
check_plugin_timesyncd = CheckPlugin(
    name="timesyncd",
    service_name="Systemd Timesyncd Time",
    sections=["timesyncd", "timesyncd_ntpmessage"],
    discovery_function=discover_timesyncd,
    check_function=check_timesyncd,
    check_default_parameters=default_check_parameters,
    check_ruleset_name="timesyncd_time",
)
