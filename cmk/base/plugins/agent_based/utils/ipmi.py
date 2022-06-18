#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from ..agent_based_api.v1 import check_levels, Metric, Result, State, type_defs

# TODO: Cleanup the whole status text mapping in utils/ipmi.py, ipmi_sensors.include, ipmi.py


@dataclass
class Sensor:
    status_txt: str
    unit: str
    value: Optional[float] = None
    crit_low: Optional[float] = None
    warn_low: Optional[float] = None
    warn_high: Optional[float] = None
    crit_high: Optional[float] = None


Section = Dict[str, Sensor]
IgnoreParams = Mapping[str, Sequence[str]]
StatusTxtMapping = Callable[[str], State]


class DiscoveryParams(TypedDict):
    discovery_mode: Union[
        Tuple[Literal["summarize"], IgnoreParams],
        Tuple[Literal["single"], IgnoreParams],
    ]


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
    return _check_ignores(sensor_name, ignore_params.get("ignored_sensors", [])) or _check_ignores(
        status_txt, ignore_params.get("ignored_sensorstates", [])
    )


def check_ipmi(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    temperature_metrics_only: bool,
    status_txt_mapping: StatusTxtMapping,
) -> type_defs.CheckResult:
    if item in ["Summary", "Summary FreeIPMI"]:
        yield from check_ipmi_summarized(
            params,
            section,
            status_txt_mapping,
        )
    elif item in section:
        yield from check_ipmi_detailed(
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


def _check_numerical_levels(
    sensor_name: str,
    val: float,
    params: Mapping[str, Any],
    unit: str,
) -> Optional[Result]:
    for this_sensorname, levels in params.get("numerical_sensor_levels", []):
        if this_sensorname == sensor_name and levels:
            result, *_ = check_levels(
                val,
                levels_upper=levels.get("upper", (None, None)),
                levels_lower=levels.get("lower", (None, None)),
                render_func=_unit_to_render_func(unit),
                label=sensor_name,
            )
            return result
    return None


def _sensor_levels_to_check_levels(
    sensor_warn: Optional[float],
    sensor_crit: Optional[float],
) -> Optional[Tuple[float, float]]:
    if sensor_crit is None:
        return None
    warn = sensor_warn if sensor_warn is not None else sensor_crit
    return warn, sensor_crit


def check_ipmi_detailed(
    item: str,
    params: Mapping[str, Any],
    sensor: Sensor,
    temperature_metrics_only: bool,
    status_txt_mapping: StatusTxtMapping,
) -> type_defs.CheckResult:

    overwrite_state = State(2)

    for wato_status_txt, wato_status in params.get("sensor_states", []):
        if sensor.status_txt.startswith(wato_status_txt):
            overwrite_state = State(wato_status)
            yield Result(state=overwrite_state, summary="User-defined state")
            break

    # stay compatible with older versions and compare with overwrite_state
    yield Result(
        state=State.best(status_txt_mapping(sensor.status_txt), overwrite_state),
        summary="Status: %s" % sensor.status_txt,
    )

    if sensor.value is not None:
        metric = None
        if not temperature_metrics_only:
            metric = Metric(
                item.replace("/", "_"),
                sensor.value,
                levels=(sensor.warn_high, sensor.crit_high),
            )

        # Do not save performance data for FANs. This produces a lot of data and is - in my
        # opinion - useless.
        elif "temperature" in item.lower() or "temp" in item.lower() or sensor.unit == "C":
            metric = Metric(
                "value",
                sensor.value,
                levels=(None, sensor.crit_high),
            )

        sensor_result, *_ = check_levels(
            sensor.value,
            levels_upper=_sensor_levels_to_check_levels(sensor.warn_high, sensor.crit_high),
            levels_lower=_sensor_levels_to_check_levels(sensor.warn_low, sensor.crit_low),
            render_func=_unit_to_render_func(sensor.unit),
        )
        yield Result(
            state=sensor_result.state,
            summary=sensor_result.summary,
        )
        if metric:
            yield metric

        num_result = _check_numerical_levels(
            item,
            sensor.value,
            params,
            sensor.unit,
        )
        if num_result is not None:
            yield num_result

    # Sensor reports 'nc' ('non critical'), so we set the state to WARNING
    if sensor.status_txt.startswith("nc"):
        yield Result(state=State.WARN, summary="Sensor is non-critical")


def check_ipmi_summarized(
    params: Mapping[str, Any],
    section: Section,
    status_txt_mapping: StatusTxtMapping,
) -> type_defs.CheckResult:
    states = [State.OK]
    warn_texts = []
    crit_texts = []
    ok_texts = []
    skipped_texts = []
    ambient_count = 0
    ambient_sum = 0.0

    for sensor_name, sensor in section.items():
        # Skip datasets which have no valid data (zero value, no unit and state nc)
        if ignore_sensor(sensor_name, sensor.status_txt, params) or (
            sensor.value == 0 and sensor.unit == "" and sensor.status_txt.startswith("nc")
        ):
            skipped_texts.append("%s (%s)" % (sensor_name, sensor.status_txt))
            continue

        txt = "%s (%s)" % (sensor_name, sensor.status_txt)
        sensor_state = status_txt_mapping(sensor.status_txt)
        for wato_status_txt, wato_status in params.get("sensor_states", []):
            if sensor.status_txt.startswith(wato_status_txt):
                sensor_state = State(wato_status)
                break

        if sensor.value is not None:
            sensor_result = _check_numerical_levels(
                sensor_name,
                sensor.value,
                params,
                sensor.unit,
            )
            if sensor_result:
                sensor_state = State.worst(sensor_state, sensor_result.state)
                txt = sensor_result.summary

            if "amb" in sensor_name or "Ambient" in sensor_name:
                ambient_count += 1
                ambient_sum += sensor.value

        if sensor_state is State.WARN:
            warn_texts.append(txt)
        elif sensor_state is State.CRIT:
            crit_texts.append(txt)
        else:
            ok_texts.append(txt)
        states.append(sensor_state)

    if ambient_count > 0:
        yield Metric(
            "ambient_temp",
            ambient_sum / ambient_count,
        )

    infotexts = ["%d sensors" % len(section)]
    for title, texts, text_state in [
        ("OK", ok_texts, State.OK),
        ("WARN", warn_texts, State.WARN),
        ("CRIT", crit_texts, State.CRIT),
        ("skipped", skipped_texts, State.OK),
    ]:
        if len(section) == len(texts):
            infotext = "%d sensors %s" % (len(section), title)
            if text_state is not State.OK:
                infotext += ": %s" % ", ".join(texts)
            yield Result(state=text_state, summary=infotext)
            return

        if texts:
            infotext = "%d %s" % (len(texts), title)
            if text_state is not State.OK:
                infotext += ": %s" % ", ".join(texts)
            infotexts.append(infotext)

    yield Result(
        state=State.worst(*states),
        summary=" - ".join(infotexts),
    )
