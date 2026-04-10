#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Self

from cmk.agent_based.v2 import check_levels, CheckResult, LevelsT, render, Result, State


@dataclass(frozen=True, kw_only=True)
class ReadingState:
    state: State
    text: str


@dataclass(frozen=True, kw_only=True)
class ReadingWithState:
    value: float
    state: ReadingState | None = None


@dataclass(frozen=True, kw_only=True)
class ElPhase:
    name: str = ""
    type: str = ""
    device_state: tuple[State, str] | None = None
    voltage: ReadingWithState | None = None
    current: ReadingWithState | None = None
    output_load: ReadingWithState | None = None
    power: ReadingWithState | None = None
    appower: ReadingWithState | None = None
    energy: ReadingWithState | None = None
    frequency: ReadingWithState | None = None
    differential_current_ac: ReadingWithState | None = None
    differential_current_dc: ReadingWithState | None = None

    # TODO: This method should be dropped, but the call sites are far from trivial...
    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        return cls(
            name=str(data.get("name", "")),
            type=str(data.get("type", "")),
            device_state=cls._parse_device_state(data.get("device_state")),
            voltage=cls._parse_reading_with_state(data.get("voltage")),
            current=cls._parse_reading_with_state(data.get("current")),
            output_load=cls._parse_reading_with_state(data.get("output_load")),
            power=cls._parse_reading_with_state(data.get("power")),
            appower=cls._parse_reading_with_state(data.get("appower")),
            energy=cls._parse_reading_with_state(data.get("energy")),
            frequency=cls._parse_reading_with_state(data.get("frequency")),
            differential_current_ac=cls._parse_reading_with_state(
                data.get("differential_current_ac")
            ),
            differential_current_dc=cls._parse_reading_with_state(
                data.get("differential_current_dc")
            ),
        )

    @staticmethod
    def _parse_device_state(value: object) -> tuple[State, str] | None:
        if value is None:
            return None
        if not isinstance(value, tuple):
            raise TypeError(value)
        return State(int(value[0])), str(value[1])

    @staticmethod
    def _parse_reading_with_state(value: object) -> ReadingWithState | None:
        if value is None:
            return None
        if isinstance(value, int | float):
            return ReadingWithState(value=value)
        if isinstance(value, tuple):
            return ReadingWithState(
                value=value[0],
                state=ReadingState(
                    state=State(int(value[1][0])),
                    text=str(value[1][1]),
                ),
            )
        raise TypeError(value)


def _to_levels(levels: object) -> LevelsT[float] | None:
    """Normalize levels to the format expected by check_levels.

    Accepts both old-style plain (warn, crit) tuples and new-style rulesets v1
    ("fixed", (warn, crit)) tuples. Returns the canonical ("fixed", (w, c))
    format or None.
    """
    if levels is None:
        return None
    if isinstance(levels, tuple) and len(levels) == 2:
        kind, values = levels
        if kind == "fixed" and isinstance(values, tuple) and len(values) == 2:
            return ("fixed", (float(values[0]), float(values[1])))
        if kind == "no_levels":
            return ("no_levels", None)
        if isinstance(kind, (int, float)) and isinstance(values, (int, float)):
            return ("fixed", (float(kind), float(values)))
    return None


def _scale_levels(levels: LevelsT[float] | None, factor: float) -> LevelsT[float] | None:
    """Scale fixed level values by a factor (e.g. mA to A conversion)."""
    match levels:
        case ("fixed", (float(warn), float(crit))):
            return ("fixed", (warn * factor, crit * factor))
        case _:
            return levels


def check_elphase(
    params: Mapping[str, Any],
    elphase: ElPhase,
) -> CheckResult:
    """Check electrical phase readings against thresholds.

    Accepts params in both old-style plain (warn, crit) tuples and new-style
    rulesets v1 ("fixed", (warn, crit)) format.
    """
    if elphase.name:
        yield Result(
            state=State.OK,
            summary=f"Name: {elphase.name}",
        )

    if elphase.type:
        yield Result(
            state=State.OK,
            summary=f"Type: {elphase.type}",
        )

    if elphase.device_state:
        device_state, device_state_readable = elphase.device_state
        device_state_str = str(int(device_state))
        if "map_device_states" in params:
            device_state_params = dict(params["map_device_states"])
            if device_state_str in device_state_params:
                state = device_state_params[device_state_str]
            elif device_state_readable in device_state_params:
                state = device_state_params[device_state_readable]
            else:
                state = State.OK
        else:
            state = device_state
        yield Result(
            state=State(state),
            summary=f"Device status: {device_state_readable}({device_state_str})",
        )

    if elphase.voltage:
        yield from _check_reading(
            elphase.voltage,
            label="Voltage",
            metric_name="voltage",
            lower_levels=_to_levels(params.get("voltage")),
            upper_levels=None,
            render_func=lambda x: f"{x:.1f} V",
        )

    if elphase.current:
        yield from _check_reading(
            elphase.current,
            label="Current",
            metric_name="current",
            lower_levels=None,
            upper_levels=_to_levels(params.get("current")),
            render_func=lambda x: f"{x:.1f} A",
        )

    if elphase.output_load:
        yield from _check_reading(
            elphase.output_load,
            label="Load",
            metric_name="output_load",
            lower_levels=None,
            upper_levels=_to_levels(params.get("output_load")),
            render_func=render.percent,
        )

    if elphase.power:
        yield from _check_reading(
            elphase.power,
            label="Power",
            metric_name="power",
            lower_levels=None,
            upper_levels=_to_levels(params.get("power")),
            render_func=lambda x: f"{x:.1f} W",
        )

    if elphase.appower:
        yield from _check_reading(
            elphase.appower,
            label="Apparent Power",
            metric_name="appower",
            lower_levels=None,
            upper_levels=_to_levels(params.get("appower")),
            render_func=lambda x: f"{x:.1f} VA",
        )

    if elphase.energy:
        yield from _check_reading(
            elphase.energy,
            label="Energy",
            metric_name="energy",
            lower_levels=None,
            upper_levels=None,
            render_func=lambda x: f"{x:.1f} Wh",
        )

    if elphase.frequency:
        if frequency_levels := params.get("frequency"):
            lower_frequency_levels = (frequency_levels[0], frequency_levels[1])
            upper_frequency_levels = (frequency_levels[2], frequency_levels[3])
        else:
            lower_frequency_levels = None
            upper_frequency_levels = None
        yield from _check_reading(
            elphase.frequency,
            label="Frequency",
            metric_name="frequency",
            lower_levels=_to_levels(lower_frequency_levels),
            upper_levels=_to_levels(upper_frequency_levels),
            render_func=lambda x: f"{x:.1f} Hz",
        )

    if elphase.differential_current_ac:
        yield from _check_reading(
            elphase.differential_current_ac,
            label="Differential current AC",
            metric_name="differential_current_ac",
            lower_levels=None,
            upper_levels=_scale_levels(_to_levels(params.get("differential_current_ac")), 1e-3),
            render_func=lambda x: f"{(x * 1e3):.1f} mA",
        )

    if elphase.differential_current_dc:
        yield from _check_reading(
            elphase.differential_current_dc,
            label="Differential current DC",
            metric_name="differential_current_dc",
            lower_levels=None,
            upper_levels=_scale_levels(_to_levels(params.get("differential_current_dc")), 1e-3),
            render_func=lambda x: f"{(x * 1e3):.1f} mA",
        )


def _check_reading(
    reading: ReadingWithState,
    *,
    label: str,
    metric_name: str,
    lower_levels: LevelsT[float] | None,
    upper_levels: LevelsT[float] | None,
    render_func: Callable[[float], str],
) -> CheckResult:
    yield from check_levels(
        reading.value,
        metric_name=metric_name,
        levels_lower=lower_levels,
        levels_upper=upper_levels,
        render_func=render_func,
        label=label,
    )

    if reading.state:
        yield Result(state=reading.state.state, summary=reading.state.text)
