#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
    LegacyResult,
)
from cmk.agent_based.v2 import any_of, equals, render, SNMPTree, StringTable
from cmk.legacy_includes.elphase import check_elphase
from cmk.legacy_includes.temperature import check_temperature, TempParamType

check_info = {}

# 508 and 604 have the same mib
janitza_umg_device_map = {
    ".1.3.6.1.4.1.34278.8.6": "96",
    ".1.3.6.1.4.1.34278.10.1": "604",
    ".1.3.6.1.4.1.34278.10.4": "508",
}


@dataclass(frozen=True)
class Total:
    power: int
    energy: int


@dataclass(frozen=True)
class Phase:
    voltage: float
    current: float
    power: int
    appower: int
    energy: float


@dataclass(frozen=True)
class Section:
    phases: Mapping[str, Phase]
    total: Total
    frequency: int
    temperature: Mapping[str, float]


def parse_janitza_umg_inphase(string_table: list[StringTable]) -> Section | None:
    if not string_table[0] or not string_table[0][0]:
        return None

    def flatten(line: StringTable) -> list[str]:
        return [x[0] for x in line]

    dev_type = janitza_umg_device_map[string_table[0][0][0]]

    info_offsets = {
        "508": {
            "energy": 4,
            "sumenergy": 5,
            "misc": 8,
        },
        "604": {
            "energy": 4,
            "sumenergy": 5,
            "misc": 8,
        },
        "96": {
            "energy": 3,
            "sumenergy": 4,
            "misc": 6,
        },
    }[dev_type]

    rmsphase = flatten(string_table[1])
    sumphase = flatten(string_table[2])
    energy = flatten(string_table[info_offsets["energy"]])
    sumenergy = flatten(string_table[info_offsets["sumenergy"]])

    if dev_type in ["508", "604"]:
        num_phases = 4
        num_currents = 4
    elif dev_type == "96":
        num_phases = 3
        num_currents = 6

    # the number of elements in each "block" within the snmp. This differs between
    # devices
    counts = [
        num_phases,  # voltages
        3,  # L1-L2, L2-L3, L3-L1
        num_currents,  # umg96 reports voltage for 3 phases and current for 6
        num_phases,  # real power
        num_phases,  # reactive power
        num_phases,  # Power in VA
        num_phases,  # Cos(Phi)
    ]

    def offset(block_id: int, phase: int) -> int:
        return sum(counts[:block_id], phase)

    # voltages are in 100mv, currents in 1mA, power in Watts / VA
    phases = {
        "Phase %d" % (phase + 1): Phase(
            voltage=int(rmsphase[offset(0, phase)]) / 10.0,
            current=int(rmsphase[offset(2, phase)]) / 1000.0,
            power=int(rmsphase[offset(3, phase)]),
            appower=int(rmsphase[offset(5, phase)]),
            energy=int(energy[phase]) / 10,
        )
        for phase in range(num_phases)
    }

    total = Total(power=int(sumphase[0]), energy=int(sumenergy[0]))

    # temperature not present in UMG508 and UMG604
    raw_frequency, *raw_temperatures = flatten(string_table[info_offsets["misc"]])

    return Section(
        phases=phases,
        total=total,
        frequency=int(raw_frequency),
        temperature={str(num): int(v) / 10.0 for num, v in enumerate(raw_temperatures, start=1)},
    )


def discover_janitza_umg_inphase(section: Section) -> LegacyDiscoveryResult:
    for item in section.phases:
        yield item, {}


def check_janitza_umg_inphase(
    item: str, params: Mapping[str, Any], section: Section
) -> LegacyCheckResult:
    if not (phase := section.phases.get(item)):
        return
    yield from check_elphase(item, params, {item: asdict(phase)})


check_info["janitza_umg"] = LegacyCheckDefinition(
    name="janitza_umg",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34278.8.6"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34278.10.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34278.10.4"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1.2",
            oids=["0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34278",
            oids=["8"],
        ),
    ],
    parse_function=parse_janitza_umg_inphase,
    service_name="Input %s",
    discovery_function=discover_janitza_umg_inphase,
    check_function=check_janitza_umg_inphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)


def discover_janitza_umg_freq(section: Section) -> LegacyDiscoveryResult:
    yield "1", {}  # why?? :-(


def check_janitza_umg_freq(
    item: str, params: Mapping[str, Any], section: Section
) -> LegacyResult | None:

    return check_levels(
        section.frequency / 100.0,
        "in_freq",
        (None, None) + params["levels_lower"],
        human_readable_func=render.frequency,
        infoname="Frequency",
    )


check_info["janitza_umg.freq"] = LegacyCheckDefinition(
    name="janitza_umg_freq",
    service_name="Frequency %s",
    sections=["janitza_umg"],
    discovery_function=discover_janitza_umg_freq,
    check_function=check_janitza_umg_freq,
    check_ruleset_name="efreq",
    check_default_parameters={"levels_lower": (0, 0)},
)


def discover_janitza_umg_temp(section: Section) -> LegacyDiscoveryResult:
    for num, temp in section.temperature.items():
        if temp != -1000:
            yield num, {}


def check_janitza_umg_temp(
    item: str, params: TempParamType, section: Section
) -> LegacyResult | None:
    if (reading := section.temperature.get(item)) is None:
        return None
    return check_temperature(reading, params, "janitza_umg_%s" % item)


check_info["janitza_umg.temp"] = LegacyCheckDefinition(
    name="janitza_umg_temp",
    service_name="Temperature External %s",
    sections=["janitza_umg"],
    discovery_function=discover_janitza_umg_temp,
    check_function=check_janitza_umg_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
