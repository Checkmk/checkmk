#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing_engine import MetricName
from cmk.gui.log import logger


@dataclass(frozen=True, kw_only=True)
class RawPerformanceValue:
    value: float
    warning: float | None = None
    critical: float | None = None
    lower_warning: float | None = None
    lower_critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class RawPerformanceData:
    check_command: str
    values: Mapping[MetricName, RawPerformanceValue]


_VALUE_AND_UNIT = re.compile(r"([0-9.,-]*)(.*)")


def _float_or_int(val: str | None) -> int | float | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _parse_range(val: str | None) -> tuple[float | None, float | None]:
    if not val:
        return None, None
    if ":" not in val:
        return None, _float_or_int(val)
    lower_str, upper_str = val.split(":", 1)
    return (
        _float_or_int(lower_str) if lower_str else None,
        _float_or_int(upper_str) if upper_str else None,
    )


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    if not value_text or value_text.isspace():
        return None, None
    value_and_unit = re.match(_VALUE_AND_UNIT, value_text)
    assert value_and_unit is not None
    return _float_or_int(value_and_unit[1]) if value_and_unit[1] else None, value_and_unit[2]


def _parse_perf_values(
    data_str: str,
) -> tuple[str, str, tuple[str | None, str | None, str | None, str | None]]:
    varname, values = data_str.split("=", 1)
    varname = varname.replace('"', "").replace("'", "")
    value_parts = values.split(";")
    value = value_parts.pop(0)
    num_fields = len(value_parts)
    return (
        varname,
        value,
        (
            value_parts[0] if num_fields > 0 else None,
            value_parts[1] if num_fields > 1 else None,
            value_parts[2] if num_fields > 2 else None,
            value_parts[3] if num_fields > 3 else None,
        ),
    )


def parse_check_command(check_command: str) -> str:
    parts = check_command.split("!", 1)
    if (
        parts[0] == "check-mk-custom"
        and len(parts) >= 2
        and (parts[1].startswith("check_ping") or "/check_ping" in parts[1])
    ):
        return "check_ping"
    return parts[0]


def _parse_perf_data(
    perf_data_string: str, check_command: str, *, debug: bool
) -> tuple[Mapping[MetricName, RawPerformanceValue], str]:
    check_command = parse_check_command(check_command)

    parts = shlex.split(perf_data_string)
    if parts and parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    check_command = check_command.replace(".", "_")

    raw_perf_data: dict[MetricName, RawPerformanceValue] = {}
    for part in parts:
        try:
            varname, value_text, value_parts = _parse_perf_values(part)
            value, unit_name = _split_unit(value_text)
            if value is None or unit_name is None:
                continue
            lower_warning, warning = _parse_range(value_parts[0])
            lower_critical, critical = _parse_range(value_parts[1])
            raw_perf_data[MetricName(varname)] = RawPerformanceValue(
                value=value,
                warning=warning,
                critical=critical,
                lower_warning=lower_warning,
                lower_critical=lower_critical,
                minimum=_float_or_int(value_parts[2]),
                maximum=_float_or_int(value_parts[3]),
            )
        except Exception as exc:
            logger.exception(
                "Failed to parse perfdata '%(perf_data_string)s'",
                {"perf_data_string": perf_data_string},
            )
            if debug:
                raise exc
    return raw_perf_data, check_command


def parse_performance_data(
    perf_data_string: str,
    check_command: str,
    rrd_metrics: Sequence[str] = (),
    *,
    debug: bool,
) -> RawPerformanceData:
    raw_perf_data, normalized_check_command = _parse_perf_data(
        perf_data_string, check_command, debug=debug
    )
    if rrd_metrics:
        rrd_only, _command = _parse_perf_data(
            " ".join(f'"{m}"=1' if " " in m else f"{m}=1" for m in rrd_metrics if "," not in m),
            check_command,
            debug=debug,
        )
        raw_perf_data = {
            **raw_perf_data,
            **{name: value for name, value in rrd_only.items() if name not in raw_perf_data},
        }
    return RawPerformanceData(check_command=normalized_check_command, values=raw_perf_data)
