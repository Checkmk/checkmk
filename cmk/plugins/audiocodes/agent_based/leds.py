#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections import Counter
from collections.abc import Container, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, StrEnum
from itertools import chain

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDBytes,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringByteTable,
)

from .lib import (
    DETECT_AUDIOCODES,
    MODULE_TYPE_MAPPING,
)

_MEDIAPACK_124 = "3"

_CHANNEL_LEDS_BY_MODULE_TYPE = {_MEDIAPACK_124: 24}


class LEDStatus(StrEnum):
    ON = auto()
    FLASHING = auto()


class LEDColor(StrEnum):
    NONE = auto()
    GREEN = auto()
    RED = auto()
    YELLOW = auto()
    ORANGE = auto()
    BLUE = auto()
    UNDEFINED = auto()
    GRAY = auto()


_COLOR_CODES = (
    LEDColor.NONE,
    LEDColor.GREEN,
    LEDColor.RED,
    LEDColor.YELLOW,
    LEDColor.ORANGE,
    LEDColor.BLUE,
    LEDColor.UNDEFINED,
    LEDColor.GRAY,
)


@dataclass(frozen=True, kw_only=True)
class LED:
    color: LEDColor
    status: LEDStatus


@dataclass(frozen=True, kw_only=True)
class ModuleLEDs:
    index: str
    module_type: str
    lit_leds: Sequence[LED]


@dataclass(frozen=True, kw_only=True)
class NamedLEDs:
    name: str
    lit_leds: Sequence[LED]


@dataclass(frozen=True, kw_only=True)
class LEDSection:
    modules: Sequence[ModuleLEDs]
    fan_trays_and_power_supplies: Sequence[NamedLEDs]


def parse_audiocodes_leds(
    string_table: Sequence[StringByteTable],
) -> LEDSection | None:
    if not string_table or all(not led_set for led_set in string_table):
        return None

    modules, fan_trays, power_supplies, redundant_fan_trays, redundant_power_supplies = string_table
    return LEDSection(
        modules=[_parse_module(row) for row in modules],
        fan_trays_and_power_supplies=[
            *(_parse_fan_tray(row, "") for row in fan_trays),
            *(_parse_fan_tray(row, " (redundant)") for row in redundant_fan_trays),
            *(_parse_power_supply(row, "") for row in power_supplies),
            *(_parse_power_supply(row, " (redundant)") for row in redundant_power_supplies),
        ],
    )


def _parse_module(row: Sequence[str | list[int]]) -> ModuleLEDs:
    match row:
        case [str(index), str(module_type), list(octets), str(num_ports)]:
            return ModuleLEDs(
                index=index,
                module_type=module_type,
                lit_leds=_decode_lit_leds(
                    octets, ignored_positions=_unavailable_channels(module_type, num_ports)
                ),
            )
        case _:
            raise ValueError(f"Unexpected module row: {row!r}")


def _parse_fan_tray(row: Sequence[str | list[int]], suffix: str) -> NamedLEDs:
    match row:
        case [str(), str(description), list(octets)]:
            return NamedLEDs(name=f"{description}{suffix}", lit_leds=_decode_lit_leds(octets))
        case _:
            raise ValueError(f"Unexpected fan tray row: {row!r}")


def _parse_power_supply(row: Sequence[str | list[int]], suffix: str) -> NamedLEDs:
    match row:
        case [str(index), list(octets)]:
            return NamedLEDs(
                name=f"Power supply {index}{suffix}", lit_leds=_decode_lit_leds(octets)
            )
        case _:
            raise ValueError(f"Unexpected power supply row: {row!r}")


def _unavailable_channels(module_type: str, num_ports: str) -> range:
    channel_leds = _CHANNEL_LEDS_BY_MODULE_TYPE.get(module_type)
    if channel_leds is None or not num_ports.isdecimal():
        return range(0)
    return range(int(num_ports), channel_leds)


def _decode_lit_leds(
    octets: Iterable[int], *, ignored_positions: Container[int] = ()
) -> Sequence[LED]:
    nibbles = (nibble for octet in octets for nibble in (octet & 0x0F, octet >> 4))
    leds = (
        LED(
            color=_COLOR_CODES[nibble >> 1],
            status=LEDStatus.FLASHING if nibble & 1 else LEDStatus.ON,
        )
        for position, nibble in enumerate(nibbles)
        if position not in ignored_positions
    )
    return [led for led in leds if led.color not in (LEDColor.NONE, LEDColor.GRAY)]


snmp_section_audiocodes_leds = SNMPSection(
    name="audiocodes_leds",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(  # module LEDs
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=[
                OIDEnd(),
                "3",  # module type
                OIDBytes("10"),  # LEDs
                "15",  # number of ports
            ],
        ),
        SNMPTree(  # fan tray
            base=".1.3.6.1.4.1.5003.9.10.10.4.22.1",
            oids=[
                OIDEnd(),
                "4",  # description
                OIDBytes("5"),  # LEDs
            ],
        ),
        SNMPTree(  # power supply
            base=".1.3.6.1.4.1.5003.9.10.10.4.23.1",
            oids=[
                OIDEnd(),
                OIDBytes("5"),  # LEDs
            ],
        ),
        SNMPTree(  # redundant fan tray
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.22.1",
            oids=[
                OIDEnd(),
                "4",  # description
                OIDBytes("5"),  # LEDs
            ],
        ),
        SNMPTree(  # redundant power supply
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.23.1",
            oids=[
                OIDEnd(),
                OIDBytes("5"),  # LEDs
            ],
        ),
    ],
    parse_function=parse_audiocodes_leds,
)


def discover_audiocodes_leds(
    section_audiocodes_module_names: Mapping[str, str] | None,  # noqa: ARG001
    section_audiocodes_leds: LEDSection | None,  # noqa: ARG001
) -> DiscoveryResult:
    yield Service()


def check_audiocodes_leds(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_leds: LEDSection | None,
) -> CheckResult:
    if section_audiocodes_leds is None:
        return

    module_names = section_audiocodes_module_names or {}
    for module in section_audiocodes_leds.modules:
        yield from _check_leds(
            _module_name(module, module_names),
            module.lit_leds,
            # On the MP-124, only the Data LED flashes red, while the device receives RTP packets.
            flashing_red_is_ok=module.module_type == _MEDIAPACK_124,
        )

    for unit in section_audiocodes_leds.fan_trays_and_power_supplies:
        yield from _check_leds(unit.name, unit.lit_leds, flashing_red_is_ok=False)

    lit_leds = chain(
        *(module.lit_leds for module in section_audiocodes_leds.modules),
        *(unit.lit_leds for unit in section_audiocodes_leds.fan_trays_and_power_supplies),
    )
    color_counts = Counter(led.color for led in lit_leds)
    if not color_counts:
        yield Result(state=State.OK, summary="No LEDs lit")
    for color, count in color_counts.items():
        yield Result(state=State.OK, summary=f"{count} {color} LED{'' if count == 1 else 's'}")


check_plugin_audiocodes_leds = CheckPlugin(
    name="audiocodes_leds",
    service_name="LED Status",
    sections=["audiocodes_module_names", "audiocodes_leds"],
    discovery_function=discover_audiocodes_leds,
    check_function=check_audiocodes_leds,
)


def _module_name(module: ModuleLEDs, module_names: Mapping[str, str]) -> str:
    if (name := module_names.get(module.index)) is not None:
        return name
    match MODULE_TYPE_MAPPING.get(module.module_type):
        case None | "acUnknown":
            return "(unknown module)"
        case type_name:
            return type_name


def _check_leds(name: str, lit_leds: Sequence[LED], *, flashing_red_is_ok: bool) -> CheckResult:
    if not lit_leds:
        return

    states = [_led_state(led, flashing_red_is_ok=flashing_red_is_ok) for led in lit_leds]
    state = State.worst(*states)
    description = _describe_leds(name, lit_leds)
    if state is State.OK:
        yield Result(state=state, notice=description)
        return
    yield Result(
        state=state,
        notice=_describe_leds(
            name, [led for led, led_state in zip(lit_leds, states) if led_state is not State.OK]
        ),
        details=description,
    )


def _led_state(led: LED, *, flashing_red_is_ok: bool) -> State:
    if flashing_red_is_ok and led.color is LEDColor.RED and led.status is LEDStatus.FLASHING:
        return State.OK
    match led.color:
        case LEDColor.GREEN:
            return State.OK
        case LEDColor.YELLOW | LEDColor.ORANGE | LEDColor.BLUE:
            return State.WARN
        case LEDColor.RED:
            return State.CRIT
        case _:
            return State.UNKNOWN


def _describe_leds(name: str, leds: Sequence[LED]) -> str:
    if len(leds) == 1:
        return f"{name} LED: {leds[0].status}-{leds[0].color}"
    counts = Counter(f"{led.status}-{led.color}" for led in leds)
    return f"{name} LEDs: " + ", ".join(f"{count} {label}" for label, count in counts.items())
