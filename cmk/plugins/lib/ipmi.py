#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State

# TODO: Cleanup the whole status text mapping in utils/ipmi.py, ipmi_sensors.include, ipmi.py


@dataclass
class Sensor:
    status_txt: str
    unit: str
    state: State | None = None
    value: float | None = None
    crit_low: float | None = None
    warn_low: float | None = None
    warn_high: float | None = None
    crit_high: float | None = None
    type_: str | None = None

    @property
    def is_present(self) -> bool:
        return not any(
            (
                "Device Removed" in self.status_txt,
                "Device Absent" in self.status_txt,
                "Entity Absent" in self.status_txt,
            )
        )

    @staticmethod
    def parse_state(dev_state: str) -> State | None:
        """Convert the state provided by FreeIPMI to a Checkmk state

        FreeIPMI maps a sensors events ("status_txt" above) to
        "nominal", "warning" or "critical".
        This mapping is configurable and well maintained, and hence
        superior to our computation of the state from the events.

        The agent not always provides this state, so we fall back to
        our own mapping -- which is known to be insufficient.
        """
        return {
            "nominal": State.OK,
            "warning": State.WARN,
            "critical": State.CRIT,
        }.get(dev_state.lower())


Section = dict[str, Sensor]
IgnoreParams = Mapping[str, Sequence[str]]
StatusTxtMapping = Callable[[str], State]


@dataclass(frozen=True)
class UserLevels:
    upper: tuple[float, float] | None
    lower: tuple[float, float] | None


class DiscoveryParams(TypedDict):
    discovery_mode: (
        tuple[Literal["summarize"], IgnoreParams] | tuple[Literal["single"], IgnoreParams]
    )


def discover_individual_sensors(
    ignore_params: IgnoreParams,
    section: Section,
) -> DiscoveryResult:
    yield from (
        Service(item=sensor_name)
        for sensor_name, sensor in section.items()
        if sensor.is_present and not ignore_sensor(sensor_name, sensor.status_txt, ignore_params)
    )


def _check_ignores(
    to_check: str,
    ignores: Sequence[str],
) -> bool:
    return any(to_check.startswith(ign) for ign in ignores)


def ignore_sensor(
    sensor_name: str,
    status_txt: str,
    ignore_params: IgnoreParams,
) -> bool:
    """
    >>> ignore_sensor("name", "status", {})
    False
    >>> ignore_sensor("name", "status", {"ignored_sensors": ["name"]})
    True
    >>> ignore_sensor("name", "status", {"ignored_sensorstates": ["status"]})
    True
    """
    return _check_ignores(
        sensor_name,
        ignore_params.get("ignored_sensors", []),
    ) or _check_ignores(
        status_txt,
        ignore_params.get("ignored_sensorstates", []),
    )


def check_ipmi(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    temperature_metrics_only: bool,
    status_txt_mapping: StatusTxtMapping,
) -> CheckResult:
    if item in ["Summary", "Summary FreeIPMI"]:
        yield from _check_ipmi_summarized(
            params,
            section,
            status_txt_mapping,
        )
    elif item in section:
        yield from _check_ipmi_detailed(
            item,
            params,
            section[item],
            temperature_metrics_only,
            status_txt_mapping,
        )


def _unit_to_render_func(unit: str) -> Callable[[float], str]:
    unit_suffix = unit and "unspecified" not in unit and " %s" % unit or ""
    unit_suffix = unit_suffix.replace("percent", "%").replace("%", "%%")
    return lambda x: ("%.2f" + unit_suffix) % x


def _compile_user_levels_map(params: Mapping[str, Any]) -> Mapping[str, UserLevels]:
    return {
        sensorname: UserLevels(
            upper=levels.get("upper"),
            lower=levels.get("lower"),
        )
        for sensorname, levels in reversed(params.get("numerical_sensor_levels", []))
    }


def _sensor_levels_to_check_levels_fixed(
    sensor_warn: float | None,
    sensor_crit: float | None,
) -> tuple[float, float] | None:
    if sensor_crit is None:
        return None
    warn = sensor_warn if sensor_warn is not None else sensor_crit
    return warn, sensor_crit


def _check_status(
    sensor: Sensor,
    status_txt_mapping: StatusTxtMapping,
    user_configured_states: Iterable[tuple[str, int]],
    label: str,
) -> Result:
    summary = f"{label}: {sensor.status_txt}"
    for status_txt_beginning, mon_state_int in user_configured_states:
        if sensor.status_txt.startswith(status_txt_beginning):
            return Result(
                state=State(mon_state_int),
                summary=summary,
                details=f"{summary} (service state set by user-configured rules)",
            )
    if sensor.state is not None:
        return Result(
            state=sensor.state,
            summary=summary,
            details=f"{summary} (service state reported by freeipmi)",
        )

    return Result(
        state=status_txt_mapping(sensor.status_txt),
        summary=summary,
        details=f"{summary} (service state derived from sensor events)",
    )


def _check_ipmi_detailed(
    item: str,
    params: Mapping[str, Any],
    sensor: Sensor,
    temperature_metrics_only: bool,
    status_txt_mapping: StatusTxtMapping,
) -> CheckResult:
    yield _check_status(sensor, status_txt_mapping, params.get("sensor_states", []), label="Status")

    if sensor.value is None:
        return

    metric = None
    if not temperature_metrics_only:
        metric = Metric(
            item.replace("/", "_"),
            sensor.value,
            levels=(sensor.warn_high, sensor.crit_high),
        )

    # Do not save performance data for FANs. This produces a lot of data and is - in my
    # opinion - useless.
    elif "temp" in item.lower() or "temp" in (sensor.type_ or "").lower() or sensor.unit == "C":
        metric = Metric(
            "value",
            sensor.value,
            levels=(None, sensor.crit_high),
        )

    sensor_result, *_ = check_levels_v1(
        sensor.value,
        levels_upper=_sensor_levels_to_check_levels_fixed(sensor.warn_high, sensor.crit_high),
        levels_lower=_sensor_levels_to_check_levels_fixed(sensor.warn_low, sensor.crit_low),
        render_func=_unit_to_render_func(sensor.unit),
    )
    yield Result(
        state=sensor_result.state,
        summary=sensor_result.summary,
    )
    if metric:
        yield metric

    user_levels_map = _compile_user_levels_map(params)
    if levels := user_levels_map.get(item):
        yield from check_levels_v1(
            sensor.value,
            levels_upper=levels.upper,
            levels_lower=levels.lower,
            render_func=_unit_to_render_func(sensor.unit),
            label=item,
        )


def _check_ipmi_summarized(
    params: Mapping[str, Any],
    section: Section,
    status_txt_mapping: StatusTxtMapping,
) -> CheckResult:
    yield from _average_ambient_temperature(section)

    yield Result(state=State.OK, summary=f"{len(section)} sensors in total")

    for title, results in _check_individual_sensors(params, section, status_txt_mapping).items():
        if not results:
            continue
        yield Result(state=results[0].state, summary=f"{len(results)} sensors {title}")
        yield from results


def _check_individual_sensors(
    params: Mapping[str, Any],
    section: Section,
    status_txt_mapping: StatusTxtMapping,
) -> Mapping[Literal["ok", "warning", "critical", "skipped"], Sequence[Result]]:
    user_levels_map = _compile_user_levels_map(params)

    # order matters!
    results: dict[Literal["ok", "warning", "critical", "skipped"], list[Result]] = {
        "ok": [],
        "warning": [],
        "critical": [],
        "skipped": [],
    }

    for sensor_name, sensor in section.items():
        # Skip datasets which have no valid data (zero value, no unit and state nc)
        if ignore_sensor(sensor_name, sensor.status_txt, params) or (
            sensor.value == 0 and sensor.unit == "" and sensor.status_txt.startswith("nc")
        ):
            results["skipped"].append(
                Result(state=State.OK, notice=f"{sensor_name}: {sensor.status_txt}")
            )
            continue

        status_result = _check_status(
            sensor, status_txt_mapping, params.get("sensor_states", []), label=sensor_name
        )

        if sensor.value is not None and (levels := user_levels_map.get(sensor_name)):
            (sensor_result,) = check_levels_v1(
                sensor.value,
                levels_upper=levels.upper,
                levels_lower=levels.lower,
                render_func=_unit_to_render_func(sensor.unit),
                label=sensor_name,
            )
            result = Result(
                state=State.worst(status_result.state, sensor_result.state),
                notice=sensor_result.summary,
                details=f"{status_result.details}, {sensor_result.details}",
            )
        else:
            result = Result(
                state=status_result.state,
                notice=status_result.summary,
                details=status_result.details,
            )

        if result.state is State.OK:
            results["ok"].append(result)
        elif result.state is State.WARN:
            results["warning"].append(result)
        else:
            results["critical"].append(result)

    return results


def _average_ambient_temperature(section: Section) -> Iterable[Metric]:
    if values := [
        sensor.value
        for sensor_name, sensor in section.items()
        if sensor.value is not None and ("amb" in sensor_name or "Ambient" in sensor_name)
    ]:
        yield Metric("ambient_temp", sum(values) / float(len(values)))
