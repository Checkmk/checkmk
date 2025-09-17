#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, render, Result, State


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


def check_elphase(
    params: Mapping[str, Any],
    elphase: ElPhase,
) -> CheckResult:
    class Bounds:
        Lower, Upper, Both = range(3)

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
        if "map_device_states" in params:
            device_state_params = dict(params["map_device_states"])
            if device_state in device_state_params:
                state = device_state_params[device_state]
            elif device_state_readable in device_state_params:
                state = device_state_params[device_state_readable]
            else:
                state = 0
        else:
            state = device_state
        yield Result(
            state=State(state),
            summary=f"Device status: {device_state_readable}({int(device_state)})",
        )

    readings: Mapping[str, ReadingWithState | None] = {
        "voltage": elphase.voltage,
        "current": elphase.current,
        "output_load": elphase.output_load,
        "power": elphase.power,
        "appower": elphase.appower,
        "energy": elphase.energy,
        "frequency": elphase.frequency,
        "differential_current_ac": elphase.differential_current_ac,
        "differential_current_dc": elphase.differential_current_dc,
    }

    for quantity, title, render_func, bound, factor in [
        ("voltage", "Voltage", lambda x: f"{x:.1f} V", Bounds.Lower, 1),
        ("current", "Current", lambda x: f"{x:.1f} A", Bounds.Upper, 1),
        ("output_load", "Load", render.percent, Bounds.Upper, 1),
        ("power", "Power", lambda x: f"{x:.1f} W", Bounds.Upper, 1),
        ("appower", "Apparent Power", lambda x: f"{x:.1f} VA", Bounds.Upper, 1),
        ("energy", "Energy", lambda x: f"{x:.1f} Wh", Bounds.Upper, 1),
        ("frequency", "Frequency", lambda x: f"{x:.1f} hz", Bounds.Both, 1),
        (
            "differential_current_ac",
            "Differential current AC",
            lambda x: f"{(x * 1000):.1f} mA",
            Bounds.Upper,
            0.001,
        ),
        (
            "differential_current_dc",
            "Differential current DC",
            lambda x: f"{(x * 1000):.1f} mA",
            Bounds.Upper,
            0.001,
        ),
    ]:
        if not (reading := readings[quantity]):
            continue

        levels_upper: tuple[float, float] | None = None
        levels_lower: tuple[float, float] | None = None
        if quantity in params:
            if bound == Bounds.Both:
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_upper = (factor * levels[0], factor * levels[1])
                if levels[2] is not None and levels[3] is not None:
                    levels_lower = (factor * levels[2], factor * levels[3])
            elif bound == Bounds.Upper:
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_upper = (factor * levels[0], factor * levels[1])
            else:  # Bounds.Lower
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_lower = (factor * levels[0], factor * levels[1])

        yield from check_levels_v1(
            reading.value * factor,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=quantity,
            render_func=render_func,
            label=title,
        )

        if reading.state:
            yield Result(state=reading.state.state, summary=reading.state.text)
