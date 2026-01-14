#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, render, SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# 508 and 604 have the same mib
janitza_umg_device_map = {
    ".1.3.6.1.4.1.34278.8.6": "96",
    ".1.3.6.1.4.1.34278.10.1": "604",
    ".1.3.6.1.4.1.34278.10.4": "508",
}


def parse_janitza_umg_inphase(string_table):
    if not string_table[0] or not string_table[0][0]:
        return None

    def flatten(line):
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

    def offset(block_id, phase):
        return sum(counts[:block_id], phase)

    # voltages are in 100mv, currents in 1mA, power in Watts / VA
    result: dict[str, float | list | int | dict] = {}

    for phase in range(num_phases):
        result["Phase %d" % (phase + 1)] = {
            "voltage": int(rmsphase[offset(0, phase)]) / 10.0,
            "current": int(rmsphase[offset(2, phase)]) / 1000.0,
            "power": int(rmsphase[offset(3, phase)]),
            "appower": int(rmsphase[offset(5, phase)]),
            "energy": int(energy[phase]) / 10,
        }

    result["Total"] = {"power": int(sumphase[0]), "energy": int(sumenergy[0])}

    misc = flatten(string_table[info_offsets["misc"]])
    result["Frequency"] = int(misc[0])
    # temperature not present in UMG508 and UMG604
    if len(misc) > 1:
        result["Temperature"] = list(map(int, misc[1:]))
    else:
        result["Temperature"] = []
    return result


def discover_janitza_umg_inphase(parsed):
    for item in parsed:
        if item.startswith("Phase"):
            yield item, {}


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
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)


def discover_janitza_umg_freq(parsed):
    # info[0] is frequency, info[1] is first temperature reading, info[2] is second.
    if "Frequency" in parsed:
        yield "1", {}  # why?? :-(


def check_janitza_umg_freq(item, params, parsed):
    if "Frequency" not in parsed:
        return None

    return check_levels(
        float(parsed["Frequency"]) / 100.0,
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


def discover_janitza_umg_temp(parsed):
    ctr = 1
    for temp in parsed["Temperature"]:
        if temp != -1000:
            yield str(ctr), {}
        ctr += 1


def check_janitza_umg_temp(item, params, parsed):
    idx = int(item) - 1
    if len(parsed["Temperature"]) > idx:
        return check_temperature(
            float(parsed["Temperature"][idx]) / 10.0, params, "janitza_umg_%s" % item
        )
    return None


check_info["janitza_umg.temp"] = LegacyCheckDefinition(
    name="janitza_umg_temp",
    service_name="Temperature External %s",
    sections=["janitza_umg"],
    discovery_function=discover_janitza_umg_temp,
    check_function=check_janitza_umg_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
