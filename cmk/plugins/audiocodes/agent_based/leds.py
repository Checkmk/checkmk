#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import auto, StrEnum
from itertools import chain
from typing import Self

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import (
    DETECT_AUDIOCODES,
)


class LEDStatus(StrEnum):
    ON = auto()
    FLASHING = auto()
    UNKNOWN = auto()


class LEDColor(StrEnum):
    NONE = auto()
    GREEN = auto()
    RED = auto()
    YELLOW = auto()
    ORANGE = auto()
    BLUE = auto()
    UNKNOWN = auto()


@dataclass(frozen=True, kw_only=True)
class LED:
    name: str | None
    status: LEDStatus
    color: LEDColor
    module_index: str | None

    @classmethod
    def from_byte(
        cls,
        name: str | None,
        byte: str,
        module_index: str | None = None,
    ) -> Self:
        led_info_byte = hex(ord(byte))[-1]
        match led_info_byte:
            case "1":
                status = LEDStatus.FLASHING
                color = LEDColor.NONE
            case "2":
                status = LEDStatus.ON
                color = LEDColor.GREEN
            case "3":
                status = LEDStatus.FLASHING
                color = LEDColor.GREEN
            case "4":
                status = LEDStatus.ON
                color = LEDColor.RED
            case "5":
                status = LEDStatus.FLASHING
                color = LEDColor.RED
            case "6":
                status = LEDStatus.ON
                color = LEDColor.YELLOW
            case "7":
                status = LEDStatus.FLASHING
                color = LEDColor.YELLOW
            case "8":
                status = LEDStatus.ON
                color = LEDColor.ORANGE
            case "9":
                status = LEDStatus.FLASHING
                color = LEDColor.ORANGE
            case "a":
                status = LEDStatus.ON
                color = LEDColor.BLUE
            case "b":
                status = LEDStatus.FLASHING
                color = LEDColor.BLUE
            case _:
                status = LEDStatus.UNKNOWN
                color = LEDColor.UNKNOWN
        return cls(name=name, status=status, color=color, module_index=module_index)

    def to_state(self):
        # Currently flashing vs not isn't taken into account, only the color
        match self.color:
            case LEDColor.GREEN:
                return State.OK
            case LEDColor.RED:
                return State.CRIT
            case LEDColor.YELLOW | LEDColor.ORANGE | LEDColor.BLUE:
                return State.WARN
            case _:
                return State.UNKNOWN


@dataclass
class LEDResults:
    module_leds: list[LED]
    fan_tray_leds: list[LED]
    power_supply_leds: list[LED]
    redundant_fan_tray_leds: list[LED]
    redundant_power_supply_leds: list[LED]


def parse_audiocodes_leds(
    string_table: Sequence[StringTable],
) -> LEDResults | None:
    if not string_table:
        return None

    module_leds = string_table[0]
    fan_tray_leds = string_table[1]
    power_supply_leds = string_table[2]
    redundant_fan_tray_leds = string_table[3]
    redundant_power_supply_leds = string_table[4]

    module_led_objs = [
        LED.from_byte(None, result[1][0], module_index=result[0]) for result in module_leds
    ]

    fan_tray_led_objs = [LED.from_byte(result[2], result[1][0]) for result in fan_tray_leds]

    power_supply_led_objs = [
        LED.from_byte(f"Power supply {result[0]}", result[1][0]) for result in power_supply_leds
    ]

    redundant_fan_tray_led_objs = [
        LED.from_byte(f"{result[2]} (redundant)", result[1][0])
        for result in redundant_fan_tray_leds
    ]

    redundant_power_supply_led_objs = [
        LED.from_byte(f"Power supply {result[0]} (redundant)", result[1][0])
        for result in redundant_power_supply_leds
    ]

    return LEDResults(
        module_leds=module_led_objs,
        fan_tray_leds=fan_tray_led_objs,
        power_supply_leds=power_supply_led_objs,
        redundant_fan_tray_leds=redundant_fan_tray_led_objs,
        redundant_power_supply_leds=redundant_power_supply_led_objs,
    )


snmp_section_audiocodes_leds = SNMPSection(
    name="audiocodes_leds",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(  # module LEDs
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=[
                OIDEnd(),
                "10",
            ],
        ),
        SNMPTree(  # fan tray
            base=".1.3.6.1.4.1.5003.9.10.10.4.22.1",
            oids=[
                OIDEnd(),
                "5",  # LEDs
                "4",  # description
            ],
        ),
        SNMPTree(  # power supply
            base=".1.3.6.1.4.1.5003.9.10.10.4.23.1",
            oids=[
                OIDEnd(),
                "5",
            ],
        ),
        SNMPTree(  # redundant fan tray
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.22.1",
            oids=[
                OIDEnd(),
                "5",  # LEDs
                "4",  # description
            ],
        ),
        SNMPTree(  # redundant power supply
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.23.1",
            oids=[
                OIDEnd(),
                "5",
            ],
        ),
    ],
    parse_function=parse_audiocodes_leds,
)


def discover_audiocodes_leds(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_leds: LEDResults | None,
) -> DiscoveryResult:
    yield Service()


def check_audiocodes_leds(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_leds: LEDResults | None,
) -> CheckResult:
    if section_audiocodes_leds is None:
        return

    color_counts: defaultdict[LEDColor, int] = defaultdict(int)
    for result in chain(
        section_audiocodes_leds.module_leds,
        section_audiocodes_leds.fan_tray_leds,
        section_audiocodes_leds.redundant_fan_tray_leds,
        section_audiocodes_leds.power_supply_leds,
        section_audiocodes_leds.redundant_power_supply_leds,
    ):
        color_counts[result.color] += 1

        # if name is None but we have a module_index, then it's a module
        # we can try to pull a name for, from another section.
        name = result.name
        if name is None and result.module_index is not None:
            if (
                section_audiocodes_module_names is not None
                and result.module_index in section_audiocodes_module_names
            ):
                name = section_audiocodes_module_names[result.module_index]
            else:
                name = "(unknown module)"

        yield Result(
            state=result.to_state(),
            notice=f"{name} LED: {result.status}-{result.color}",
        )

    for color, count in color_counts.items():
        yield Result(state=State.OK, summary=f"{count} {color} LED{'' if count == 1 else 's'}")


check_plugin_audiocodes_leds = CheckPlugin(
    name="audiocodes_leds",
    service_name="LED Status",
    sections=["audiocodes_module_names", "audiocodes_leds"],
    discovery_function=discover_audiocodes_leds,
    check_function=check_audiocodes_leds,
)
