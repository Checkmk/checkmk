# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# (c) 2024 SWR; original author Frank Baier <frank.baier@swr.de>
"""Shared PDU2-MIB residual-current parsing and evaluation for inlets and poles."""

from typing import Literal, NotRequired, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    Metric,
    NoLevelsT,
    CheckPlugin,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.raritan.lib import ResidualSensor, ResidualSection, STATE_MAPPING, PduSection


class Params(TypedDict):
    warn_missing_data: bool
    warn_missing_levels: bool
    residual_levels: NotRequired[NoLevelsT | FixedLevelsT[float]]
    residual_ac_levels: NotRequired[NoLevelsT | FixedLevelsT[float]]
    residual_dc_levels: NotRequired[NoLevelsT | FixedLevelsT[float]]


type Section = ResidualSection

type ResidualParameter = Literal["residual_levels", "residual_ac_levels", "residual_dc_levels"]

_RESIDUAL_TYPES: dict[str, tuple[str, str, ResidualParameter]] = {
    "26": ("residual_current", "Residual Current", "residual_levels"),
    "55": ("residual_current_ac", "Residual Current AC", "residual_ac_levels"),
    "36": ("residual_current_dc", "Residual Current DC", "residual_dc_levels"),
}
_RCM_STATES = {
    "-1": (State.UNKNOWN, "unavailable"),
    "4": (State.OK, "normal"),
    "14": (State.CRIT, "fail"),
    "27": (State.WARN, "warning"),
    "28": (State.CRIT, "critical"),
    "29": (State.WARN, "self test"),
}


def discover_residual_current(
        section: ResidualSection
) -> DiscoveryResult:
    for item, sensors in section.items():
        if any(sensor.available and kind in {*_RESIDUAL_TYPES, "27"} for kind, sensor in sensors.items()):
            yield Service(item=item)


def _render_current(
        value: float
) -> str:
    return f"{value * 1000:.1f} mA"


def _check_sensor(
        params: Params,
        sensor: ResidualSensor
) -> CheckResult:
    metric, label, parameter = _RESIDUAL_TYPES[sensor.index.sensor_type]
    if sensor.value is None:
        yield Result(
            state=State.WARN if params.get("warn_missing_data") else State.OK,
            summary=f"{label}: no measurement available",
        )
        return

    upper, lower = sensor.upper, sensor.lower
    if parameter in params:
        configured = params[parameter]
        upper = configured[1] if configured[0] == "fixed" else (None, None)
        lower = (None, None)
    elif upper[0] in (None, 0) and upper[1] is not None:
        # Device WARN=0 or a disabled/missing WARN uses the active CRIT limit.
        # Explicit rule values, including zero, are never replaced.
        upper = (upper[1], upper[1])
    elif upper[0] is not None and upper[1] is None:
        # A sole active device WARN limit also supplies the CRIT limit.
        upper = (upper[0], upper[0])
    warn, crit = upper
    lower_warn, lower_crit = lower
    value = sensor.value
    state, state_text = STATE_MAPPING.get(sensor.state, (State.UNKNOWN, "unhandled state"))
    details = []
    for threshold, level, direction in (
            (warn, State.WARN, "above"), (crit, State.CRIT, "above"),
            (lower_warn, State.WARN, "below"), (lower_crit, State.CRIT, "below"),
    ):
        if threshold is not None and (value >= threshold if direction == "above" else value < threshold):
            state = State.worst(state, level)
            details.append(f"{direction} {level.name} at {_render_current(threshold)}")
    if sensor.state != "4":
        details.append(f"sensor state: {state_text}")
    suffix = f" ({', '.join(details)})" if details else ""
    yield Result(state=state, summary=f"{label}: {_render_current(value)}{suffix}")
    yield Metric(metric, value, levels=upper if upper != (None, None) else None)


def check_residual_current(
        item: str,
        params: Params,
        section: ResidualSection
) -> CheckResult:
    sensors = section.get(item, {})
    residual_sensors = [
        sensors[kind] for kind in _RESIDUAL_TYPES
        if kind in sensors and sensors[kind].available
    ]
    rcm = sensors.get("27")
    if rcm is not None and not rcm.available:
        rcm = None
    if not residual_sensors and rcm is None:
        yield Result(
            state=State.WARN if params.get("warn_missing_data") else State.OK,
            summary="No residual operating current available!",
        )
        return

    for sensor in residual_sensors:
        yield from _check_sensor(params, sensor)

    # Preserve the historical percentage, using current from this exact inlet/pole only.
    if (total := sensors.get("1")) is not None and total.value:
        if (residual := sensors.get("26")) is not None and residual.value is not None:
            yield from check_levels(
                residual.value / total.value * 100,
                metric_name="residual_current_percentage",
                label="Residual Current Percentage",
                render_func=render.percent,
                notice_only=True,
            )

    if rcm is not None:
        state, text = _RCM_STATES.get(rcm.state, (State.UNKNOWN, f"unhandled state {rcm.state}"))
        yield Result(state=state, summary=f"RCM state: {text}")

    # Combined-current sensors normally carry the RCM's alarm limits. Optional
    # AC/DC diagnostic components without separate limits must not cause WARN.
    primary_sensors = [sensor for sensor in residual_sensors if sensor.index.sensor_type == "26"]
    if not primary_sensors:
        primary_sensors = residual_sensors
    for sensor in primary_sensors:
        if sensor.value is None:
            continue
        _metric, label, parameter = _RESIDUAL_TYPES[sensor.index.sensor_type]
        configured = params.get(parameter)
        if configured is not None or any(level is not None for level in (*sensor.upper, *sensor.lower)):
            continue
        yield Result(
            state=State.WARN if params.get("warn_missing_levels") else State.OK,
            notice=f"{label}: missing warn/crit levels!",
        )


def check_residual_current_section(item: str, params: Params, section: PduSection) -> CheckResult:
    """Report invalid numeric data without emitting unusable current metrics."""
    if section.residual_error is not None:
        yield Result(state=State.UNKNOWN, summary=f"Invalid residual current data: {section.residual_error}")
        return
    yield from check_residual_current(item, params, section.get_residual())


def discover_raritan_pdu_residual_current_summary(
        section: PduSection
) -> DiscoveryResult:
    yield from discover_residual_current(section.get_residual())


def check_raritan_pdu_residual_current_summary(
        item: str,
        params: Params,
        section: PduSection
) -> CheckResult:
    yield from check_residual_current_section(item, params, section)


check_plugin_raritan_pdu_residual_current_summary = CheckPlugin(
    name="raritan_pdu_residual_current_summary",
    sections=["raritan_pdu_inlet_summary"],
    service_name="Residual Current %s",
    discovery_function=discover_raritan_pdu_residual_current_summary,
    check_function=check_raritan_pdu_residual_current_summary,
    check_ruleset_name="residual_current",
    check_default_parameters=Params(warn_missing_data=True, warn_missing_levels=True),
)
