#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import math
import time
from collections.abc import Generator, Iterator, MutableMapping, Sequence
from typing import Any, overload, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, get_average, get_rate, Metric, Result, State
from cmk.agent_based.v2.render import timespan

StatusType = int
TempUnitType = str
LevelModes = str

TwoLevelsType = tuple[float | None, float | None]
FourLevelsType = tuple[float | None, float | None, float | None, float | None]
LevelsType = TwoLevelsType | FourLevelsType


class TrendComputeDict(TypedDict, total=False):
    period: int
    trend_levels: TwoLevelsType
    trend_levels_lower: TwoLevelsType
    trend_timeleft: TwoLevelsType


class TempParamDict(TypedDict, total=False):
    input_unit: TempUnitType
    output_unit: TempUnitType
    levels: TwoLevelsType
    levels_lower: TwoLevelsType
    device_levels_handling: LevelModes
    trend_compute: TrendComputeDict


TempParamType = None | TwoLevelsType | FourLevelsType | TempParamDict


def fahrenheit_to_celsius(tempf, relative=False):
    if tempf is None:
        return None

    if relative:
        return float(tempf) * (5.0 / 9.0)
    return (float(tempf) - 32) * (5.0 / 9.0)


def celsius_to_fahrenheit(tempc, relative=False):
    if tempc is None:
        return None

    if relative:
        return float(tempc) * (9.0 / 5.0)
    return (float(tempc) * (9.0 / 5.0)) + 32


def to_celsius(reading, unit, relative=False):
    if isinstance(reading, tuple):
        return tuple(to_celsius(x, unit, relative) for x in reading)
    if unit == "f":
        return fahrenheit_to_celsius(reading, relative)
    if unit == "k":
        if relative:
            return reading
        if reading is None:
            return None
        return reading - 273.15
    return reading


def from_celsius(tempc, unit, relative=False):
    if unit == "f":
        return celsius_to_fahrenheit(tempc, relative)
    if unit == "k":
        if relative:
            return tempc
        return tempc + 273.15
    return tempc


# Format number according to its datatype
def render_temp(n: float, output_unit: str, relative: bool = False, *, sign: bool = False) -> str:
    """
    >>> render_temp(12., "c", False, sign=False)
    '12.0'
    >>> render_temp(12, "c", False, sign=True)
    '+12'
    >>> render_temp(-12., "f", False, sign=False)
    '10.4'

    """
    value = from_celsius(n, output_unit, relative)
    template = "%{}{}".format("+" if sign else "", "d" if isinstance(n, int) else ".1f")
    return template % value


def _render_temp_with_unit(temp: float, unit: str) -> str:
    return f"{render_temp(temp, unit)} {temp_unitsym[unit]}"


temp_unitsym = {
    "c": "°C",
    "f": "°F",
    "k": "K",
}


def _migrate_params(params: TempParamType) -> TempParamDict:
    """Migrate legacy params values to the current one.

    Args:
        params: Anything which was once a valid params entry. Concretely, 2-tuples, 4-tuples and
                dicts with the correct values are allowed. In the case of a dict, nothing is done.

    Returns:
        A dict.

    Examples:

        >>> _migrate_params((1, 2))
        {'levels': (1, 2)}

        >>> _migrate_params((1, 2, 3, 4))
        {'levels': (1, 2), 'levels_lower': (3, 4)}

        >>> _migrate_params({})
        {}

        >>> _migrate_params(None)
        {}

    """
    # Convert legacy tuple params into new dict
    if isinstance(params, tuple):
        if len(params) == 4:
            params = {
                "levels": params[:2],
                "levels_lower": params[2:],
            }
        else:
            params = {"levels": params[:2]}
    elif params is None:
        params = {}
    return params


def parse_levels(
    levels: tuple[float | None, float | None] | None = None,
) -> tuple[float, float] | None:
    if levels is None:
        return None

    warn, crit = levels
    if warn is None or crit is None:
        return None

    return warn, crit


def _check_trend(
    value_store: MutableMapping[str, Any],
    temp: float,
    params: TrendComputeDict,
    output_unit: str,
    crit_temp: float | None,
    crit_temp_lower: float | None,
    unique_name: str,
) -> Generator[Result, None, None]:
    trend_range_min = params["period"]
    this_time = time.time()

    # current rate since last check
    rate = get_rate(
        value_store=value_store,
        key="temp.%s.delta" % unique_name,
        time=this_time,
        value=temp,
    )

    rate_avg = get_average(
        value_store=value_store,
        key="temp.%s.trend" % unique_name,
        time=this_time,
        value=rate,
        backlog_minutes=trend_range_min,
    )

    trend = rate_avg * trend_range_min * 60.0
    levels_upper_trend = parse_levels(params.get("trend_levels"))

    levels_lower_trend = parse_levels(params.get("trend_levels_lower"))
    if levels_lower_trend is not None:
        # GUI representation of this parameter is labelled 'temperature decrease'; the user may input this
        # as a positive or negative value
        levels_lower_trend = (abs(levels_lower_trend[0]) * -1, abs(levels_lower_trend[1]) * -1)

    yield from check_levels_v1(
        value=trend,
        levels_upper=levels_upper_trend,
        levels_lower=levels_lower_trend,
        label="Temperature trend",
        render_func=lambda trend: render_temp(
            trend,
            output_unit,
            relative=True,
            sign=True,
        )
        + " "
        + temp_unitsym[output_unit]
        + " per "
        + str(trend_range_min)
        + " min",
    )

    if "trend_timeleft" not in params:
        return

    limit = crit_temp if trend > 0 else crit_temp_lower
    if limit is None:
        # crit levels may not be set
        return

    # compute time until temperature limit is reached
    warn_timeleft_min, crit_timeleft_min = params["trend_timeleft"]
    if warn_timeleft_min is None or crit_timeleft_min is None:
        levels_timeleft_sec = None
    else:
        levels_timeleft_sec = (warn_timeleft_min * 60.0, crit_timeleft_min * 60.0)

    diff_to_limit = limit - temp
    if rate_avg != 0 and not math.isinf(seconds_left := float(diff_to_limit / rate_avg)):
        yield from check_levels_v1(
            value=seconds_left,
            levels_lower=levels_timeleft_sec,
            render_func=timespan,
            label="Time until temperature limit reached",
        )


class TemperatureResult:
    def __init__(
        self, *, metric: Metric, reading: Result, trends: Sequence[Result], config: Result
    ) -> None:
        self.metric = metric
        self.reading = reading
        self.trends = trends
        self.config = config
        self._iter: Iterator[Result | Metric] = iter(
            (self.metric, self.reading, *self.trends, self.config)
        )

    def __iter__(self) -> Iterator[Result | Metric]:
        return self._iter

    def __next__(self) -> Result | Metric:
        return next(self._iter)


@overload
def check_temperature(
    reading: float,
    params: TempParamType,
    *,
    unique_name: str,
    value_store: MutableMapping[str, Any],
    dev_unit: str | None = "c",
    dev_levels: tuple[float, float] | None = None,
    dev_levels_lower: tuple[float, float] | None = None,
    dev_status: StatusType | None = None,
    dev_status_name: str | None = None,
) -> TemperatureResult: ...


@overload
def check_temperature(
    reading: float,
    params: TempParamType,
    *,
    unique_name: None = None,
    value_store: None = None,
    dev_unit: str | None = "c",
    dev_levels: tuple[float, float] | None = None,
    dev_levels_lower: tuple[float, float] | None = None,
    dev_status: StatusType | None = None,
    dev_status_name: str | None = None,
) -> TemperatureResult: ...


def check_temperature(
    reading: float,
    params: TempParamType,
    *,
    unique_name: str | None = None,
    value_store: MutableMapping[str, Any] | None = None,
    dev_unit: str | None = "c",
    dev_levels: tuple[float, float] | None = None,
    dev_levels_lower: tuple[float, float] | None = None,
    dev_status: StatusType | None = None,
    dev_status_name: str | None = None,
) -> TemperatureResult:
    """This function checks the temperature value against specified levels and issues a warn/cirt
    message. Levels can be supplied by the user or the device. The user has the possibility to configure
    the preferred levels. Additionally, it is possible to check temperature trends. All internal
    computations are done in Celsius.

    Args:
        reading: The numeric temperature value itself.
        params: A dictionary giving the user's configuration. See below.
        unique_name: The name under which to track performance data for trend computation.
        value_store: The Value Store to used for trend computation
        dev_unit: The unit. May be one of 'c', 'f' or 'k'. Default is 'c'.
        dev_levels: The upper levels (warn, crit)
        dev_levels_lower: The lower levels (warn, crit)
        dev_status: The status according to the device itself.
        dev_status_name: The device's own name for the status.

    Configuration:
        The parameter "params" may contain user configurable settings with the following keys:
            - input_unit -- The device's unit, user defined.
            - output_unit -- The unit by which to report.
            - levels -- Upper levels, user defined.
            - levels_lower -- Lower levels, user defined.
            - device_levels_handling -- One of the following modes:
                - usrdefault (default) -- Use user's levels, if not there use device's levels.
                - usr -- Always use user's levels. Ignore device's levels.
                - devdefault -- Use device's levels, if not there use user's levels.
                - dev -- Always use device's levels. Ignore users's levels.
                - best -- Report the least critical status of user's and device's levels.
                - worst -- Report the most critical status of user's and device's levels.
            - trend_compute -- If set calculates temperature trend:
                - period -- The period for the trend computation in minutes, e.g. rise of 12°/60 min
                - trend_levels -- Temperature increase per period. (warn, crit)
                - trend_levels_lower -- Temperature decrease per period. (warn, crit)
                - trend_timeleft -- Time left until a CRITICAL temperature level is reached (upper or lower).

    GUI:
         - cmk/gui/plugins/wato/check_parameters/temperature.py

    """
    if (unique_name is None) ^ (value_store is None):
        raise ValueError(
            "Cannot compute trend. Either specify both variables 'unique_name' and 'value_store'"
            " or none."
        )

    # Convert legacy tuple params into new dict
    params = _migrate_params(params)

    input_unit = params.get("input_unit", dev_unit)
    output_unit = params.get("output_unit", "c")
    temp = to_celsius(reading, input_unit)

    # User levels are already in Celsius
    usr_levels_upper = parse_levels(params.get("levels"))
    usr_levels_lower = parse_levels(params.get("levels_lower"))
    dev_levels_upper = to_celsius(dev_levels, dev_unit)
    dev_levels_lower = to_celsius(dev_levels_lower, dev_unit)

    device_levels_handling = params.get("device_levels_handling", "usrdefault")

    usr_result, usr_metric = check_levels_v1(
        value=temp,
        metric_name="temp",
        levels_upper=usr_levels_upper,
        levels_lower=usr_levels_lower,
        label="Temperature",
        render_func=lambda temp: _render_temp_with_unit(temp, output_unit),
    )
    assert isinstance(usr_result, Result)
    assert isinstance(usr_metric, Metric)

    dev_result, dev_metric = check_levels_v1(
        value=temp,
        metric_name="temp",
        levels_upper=dev_levels_upper,
        levels_lower=dev_levels_lower,
        label="Temperature",
        render_func=lambda temp: _render_temp_with_unit(temp, output_unit),
    )
    assert isinstance(dev_result, Result)
    assert isinstance(dev_metric, Metric)

    usr_extended_results: list[Result] = []
    dev_extended_results: list[Result] = []
    if (
        unique_name is not None
        and value_store is not None
        and params.get("trend_compute") is not None
    ):
        usr_extended_results.extend(
            result
            for result in _check_trend(
                value_store=value_store,
                temp=temp,
                params=params["trend_compute"],
                output_unit=output_unit,
                crit_temp=usr_levels_upper[1] if usr_levels_upper is not None else None,
                crit_temp_lower=usr_levels_lower[1] if usr_levels_lower is not None else None,
                unique_name=unique_name,
            )
        )

        dev_extended_results.extend(
            result
            for result in _check_trend(
                value_store=value_store,
                temp=temp,
                params=params["trend_compute"],
                output_unit=output_unit,
                crit_temp=dev_levels_upper[1] if dev_levels_upper is not None else None,
                crit_temp_lower=dev_levels_lower[1] if dev_levels_lower is not None else None,
                unique_name=unique_name + ".dev",
            )
        )

    if dev_status is not None:
        dev_extended_results.append(
            Result(
                state=State(dev_status),
                notice="State on device: %s" % dev_status_name,
            )
        )

    if device_levels_handling == "usr":
        return TemperatureResult(
            metric=usr_metric,
            reading=usr_result,
            trends=usr_extended_results,
            config=Result(state=State.OK, notice="Configuration: only use user levels"),
        )

    if device_levels_handling == "dev":
        return TemperatureResult(
            metric=dev_metric,
            reading=dev_result,
            trends=dev_extended_results,
            config=Result(state=State.OK, notice="Configuration: only use device levels"),
        )

    if device_levels_handling == "usrdefault":
        if usr_levels_upper is not None or usr_levels_lower is not None:
            return TemperatureResult(
                metric=usr_metric,
                reading=usr_result,
                trends=usr_extended_results,
                config=_make_preferred_result("user", "device", "(used user levels)"),
            )

        if dev_levels_upper is not None or dev_levels_lower is not None:
            return TemperatureResult(
                metric=dev_metric,
                reading=dev_result,
                trends=dev_extended_results,
                config=_make_preferred_result("user", "device", "(used device levels)"),
            )

        return TemperatureResult(
            metric=usr_metric,
            reading=usr_result,
            trends=usr_extended_results,
            config=_make_preferred_result("user", "device", "(no levels found)"),
        )

    if device_levels_handling == "devdefault":
        if dev_levels_upper is not None or dev_levels_lower is not None:
            return TemperatureResult(
                metric=dev_metric,
                reading=dev_result,
                trends=dev_extended_results,
                config=_make_preferred_result("device", "user", "(used device levels)"),
            )

        if usr_levels_upper is not None or usr_levels_lower is not None:
            return TemperatureResult(
                metric=usr_metric,
                reading=usr_result,
                trends=usr_extended_results,
                config=_make_preferred_result("device", "user", "(used user levels)"),
            )

        return TemperatureResult(
            metric=dev_metric,
            reading=dev_result,
            trends=dev_extended_results,
            config=_make_preferred_result("device", "user", "(no levels found)"),
        )

    usr_overall_state = State.worst(
        usr_result.state, *(result.state for result in usr_extended_results)
    )
    dev_overall_state = State.worst(
        dev_result.state, *(result.state for result in dev_extended_results)
    )

    if device_levels_handling == "worst":
        worst_state = State.worst(usr_overall_state, dev_overall_state)

        if usr_overall_state == worst_state:
            return TemperatureResult(
                metric=usr_metric,
                reading=usr_result,
                trends=usr_extended_results,
                config=Result(state=State.OK, notice="Configuration: show most critical state"),
            )

        return TemperatureResult(
            metric=dev_metric,
            reading=dev_result,
            trends=dev_extended_results,
            config=Result(state=State.OK, notice="Configuration: show most critical state"),
        )

    if device_levels_handling == "best":
        best_state = State.best(usr_overall_state, dev_overall_state)

        if usr_overall_state == best_state:
            return TemperatureResult(
                metric=usr_metric,
                reading=usr_result,
                trends=usr_extended_results,
                config=Result(state=State.OK, notice="Configuration: show least critical state"),
            )

        return TemperatureResult(
            metric=dev_metric,
            reading=dev_result,
            trends=dev_extended_results,
            config=Result(state=State.OK, notice="Configuration: show least critical state"),
        )

    raise ValueError(f"Unknown device_levels_handling: {device_levels_handling}")


def _make_preferred_result(
    winner: str,
    looser: str,
    suffix: str,
) -> Result:
    return Result(
        state=State.OK,
        notice=f"Configuration: prefer {winner} levels over {looser} levels {suffix}",
    )


@dataclasses.dataclass(frozen=True)
class TemperatureSensor:
    id: str
    temp: float
    result: Result


def aggregate_temperature_results(
    sensorlist: Sequence[TemperatureSensor],
    params: TempParamDict,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    """This function checks a list of temperature values against specified levels and issues a warn/cirt
    message. Levels can be supplied by the user or the device. The user has the possibility to configure
    the preferred levels. Additionally, it is possible to check temperature trends. All internal
    computations are done in Celsius.

    Args:
        sensorlist: A sequence of sensors containing the sensor ID, the temperature value, and the single sensor's result.
        params: A dictionary giving the user's configuration.
        value_store: The Value Store to used for trend computation
    """

    if not sensorlist:
        return

    sensor_count = len(sensorlist)
    yield Result(state=State.OK, summary=f"Sensors: {sensor_count}")

    output_unit = params.get("output_unit", "c")
    unitsym = temp_unitsym[output_unit]

    tempmax = max(s.temp for s in sensorlist)
    yield Result(state=State.OK, summary=f"Highest: {render_temp(tempmax, output_unit)} {unitsym}")
    yield Metric("temp", tempmax)

    tempavg = sum(s.temp for s in sensorlist) / float(sensor_count)
    yield Result(state=State.OK, summary=f"Average: {render_temp(tempavg, output_unit)} {unitsym}")

    tempmin = min(s.temp for s in sensorlist)
    yield Result(state=State.OK, summary=f"Lowest: {render_temp(tempmin, output_unit)} {unitsym}")

    yield from (
        Result(state=s.result.state, summary=f"{s.id}: {s.result.summary}")
        for s in sensorlist
        if s.result.state != State.OK
    )

    if "trend_compute" in params and "period" in params["trend_compute"]:
        usr_crit, usr_crit_lower = None, None
        if (user_levels := params.get("levels")) is not None:
            _, usr_crit = user_levels

        if (user_levels_lower := params.get("levels_lower")) is not None:
            _, usr_crit_lower = user_levels_lower

        yield from _check_trend(
            value_store=value_store,
            temp=tempavg,
            params=params["trend_compute"],
            output_unit=output_unit,
            crit_temp=usr_crit,
            crit_temp_lower=usr_crit_lower,
            unique_name="overall_trend",
        )
