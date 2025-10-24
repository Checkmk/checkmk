#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG

#   .--general-------------------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+


# See mbgLtNgRefclockType in MIB
REFCLOCK_TYPES = {
    "0": "unknown",
    "1": "gps166",
    "2": "gps167",
    "3": "gps167SV",
    "4": "gps167PC",
    "5": "gps167PCI",
    "6": "gps163",
    "7": "gps168PCI",
    "8": "gps161",
    "9": "gps169PCI",
    "10": "tcr167PCI",
    "11": "gps164",
    "12": "gps170PCI",
    "13": "pzf511",
    "14": "gps170",
    "15": "tcr511",
    "16": "am511",
    "17": "msf511",
    "18": "grc170",
    "19": "gps170PEX",
    "20": "gps162",
    "21": "ptp270PEX",
    "22": "frc511PEX",
    "23": "gen170",
    "24": "tcr170PEX",
    "25": "wwvb511",
    "26": "mgr170",
    "27": "jjy511",
    "28": "pzf600",
    "29": "tcr600",
    "30": "gps180",
    "31": "gln170",
    "32": "gps180PEX",
    "33": "tcr180PEX",
    "34": "pzf180PEX",
    "35": "mgr180",
    "36": "msf600",
    "37": "wwvb600",
    "38": "jjy600",
    "39": "gps180HS",
    "40": "gps180AMC",
    "41": "esi180",
    "42": "cpe180",
    "43": "lno180",
    "44": "grc180",
    "45": "liu",
    "46": "dcf600HS",
    "47": "dcf600RS",
    "48": "mri",
    "49": "bpe",
    "50": "gln180Pex",
    "51": "n2x",
    "52": "rsc180",
    "53": "lneGb",
    "54": "lnePpg180",
    "55": "scg",
    "56": "mdu300",
    "57": "sdi",
    "58": "fdm180",
    "59": "spt",
    "60": "pzf180",
    "61": "rel1000",
    "62": "hps100",
    "63": "vsg180",
    "64": "msf180",
    "65": "wwvb180",
    "66": "cpc180",
    "67": "ctc100",
    "68": "tcr180",
    "69": "lue180",
    "70": "cpc01",
    "71": "tsu01",
    "72": "cmc01",
    "73": "scu01",
    "74": "fcu01",
    "75": "mssb100",
    "76": "lne180sfp",
    "77": "gts180",
    "78": "gps180csm",
    "79": "grc181",
    "80": "n2x180",
    "81": "gns180pex",
    "82": "mdu180",
    "83": "mdu312",
    "84": "gps165",
    "85": "gns181uc",
    "86": "psx4GE",
    "87": "rsc180rdu",
    "88": "cpc200",
    "89": "fdm180m",
    "90": "lsg180",
    "91": "gps190",
    "92": "gns181",
    "93": "pio180",
    "94": "fcm180",
    "95": "tcr180usb",
    "96": "ssp100",
    "97": "gns165",
    "98": "rsc180rdmp",
    "99": "gps16x",
    "100": "mshps100",
    "101": "bpestm",
    "102": "vsi180",
    "103": "gnm181",
    "104": "rscrduttl",
    "105": "rsc2000",
    "106": "fcu200",
    "107": "rel1000rc",
    "108": "wsiug2864",
    "109": "vsg181",
    "110": "bps2xxx",
    "111": "bpe2352",
    "112": "bpe8XXX",
    "113": "bpe6042",
    "114": "gns190",
    "115": "gps180msbc",
    "116": "gns181msbc",
    "117": "gns181ucmsbc",
    "118": "prs181",
    "119": "ecm180",
    "120": "mro181",
    "121": "vsg181msbc",
    "122": "scg181",
    "123": "nimbra100",
    "124": "rsc180scu",
    "125": "pmu190",
    "126": "gns190uc",
    "127": "vmx180",
    "128": "rcg181",
    "129": "gns191",
    "130": "vsg181h",
    "131": "gps182",
    "132": "rsc1000",
    "133": "gns182",
    "134": "gns182uc",
    "135": "gsr190",
    "136": "gen182",
    "137": "cpe182",
    "138": "fdm182",
    "139": "fdm182m",
    "140": "pzf182",
    "141": "pzf183",
    "142": "bpe8nnn",
    "143": "n2x185",
    "144": "anz141",
    "145": "msf182",
    "146": "rel1002",
    "147": "gns183",
    "148": "gxl183",
    "149": "m3t",
}
# See mbgLtNgRefclockUsage in MIB
REFCLOCK_USAGES = {
    "0": "not available",
    "1": "secondary",
    "2": "compare",
    "3": "primary",
}
# See mbgLtNgRefclockState in MIB
REFCLOCK_STATES = {
    "0": "not available",  # CRIT
    "1": "synchronized",  # OK
    "2": "not synchronized",  # WARN
}
REFCLOCK_STATES_STATE = {
    "0": State.CRIT,
    "1": State.OK,
    "2": State.WARN,
}
# See mbgLtNgRefclockSubstate in MIB
REFCLOCK_SUBSTATES = {
    "-1": "MRS Ref None",
    "0": "not available",
    "1": "GPS sync",
    "2": "GPS tracking",
    "3": "GPS antenna disconnected",
    "4": "GPS warm boot",
    "5": "GPS cold boot",
    "6": "GPS antenna short circuit",
    "50": "LW never sync",
    "51": "LW not sync",
    "52": "LW sync",
    "100": "TCR not sync",
    "101": "TCT sync",
    "149": "MRS internal oscillator sync",
    "150": "MRS GPS sync",
    "151": "MRS 10Mhz sync",
    "152": "MRS PPS in sync",
    "153": "MRS 10Mhz PPS in sync",
    "154": "MRS IRIG sync",
    "155": "MRS NTP sync",
    "156": "MRS PTP IEEE 1588 sync",
    "157": "MRS PTP over E1 sync",
    "158": "MRS fixed frequency in sync",
    "159": "MRS PPS string sync",
    "160": "MRS variable frequency GPIO sync",
    "161": "MRS reserved",
    "162": "MRS DCF77 PZF sync",
    "163": "MRS longwave sync",
    "164": "MRS GLONASS GPS sync",
    "165": "MRS HAVE QUICK sync",
    "166": "MRS external oscillator sync",
    "167": "MRS SyncE",
    "168": "MRS video in sync",
    "169": "MRS ltc sync",
    "170": "MRS osc sync",
}


@dataclass
class RefClock:
    item: str
    clock_type: str
    usage: str
    state: str
    substate: str
    status_a: int
    max_status_a: int
    status_b: int
    max_status_b: int
    info: str
    leapsecond_date: str

    def _get_verbose_name(self, value: str, mapping: Mapping[str, str]) -> str | None:
        return mapping.get(value, None)

    @property
    def verbose_clock_type(self) -> str:
        return (
            self._get_verbose_name(self.clock_type, REFCLOCK_TYPES)
            or f"unknown ({self.clock_type})"
        )

    @property
    def verbose_usage(self) -> str | None:
        return self._get_verbose_name(self.usage, REFCLOCK_USAGES)

    @property
    def verbose_state(self) -> str | None:
        return self._get_verbose_name(self.state, REFCLOCK_STATES)

    @property
    def verbose_substate(self) -> str | None:
        return self._get_verbose_name(self.substate, REFCLOCK_SUBSTATES)

    @property
    def is_gps(self) -> bool | None:
        if self.clock_type not in REFCLOCK_TYPES:
            return None
        return "gps" in self.verbose_clock_type

    @property
    def result_state(self) -> State:
        state = REFCLOCK_STATES_STATE.get(self.state, State.UNKNOWN)
        type_state = State.OK if self.clock_type in REFCLOCK_TYPES else State.WARN
        return State.worst(state, type_state)


ParsedSection = Mapping[str, RefClock]


def mbg_lantime_ng_generalstate(refclock: RefClock) -> Result:
    detailed_state_txt = " (%s)" % refclock.verbose_substate if refclock.substate != "0" else ""
    infotext = f"Type: {refclock.verbose_clock_type}, Usage: {refclock.verbose_usage}, State: {refclock.verbose_state}{detailed_state_txt}"

    return Result(state=refclock.result_state, summary=infotext)


# .
#   .--gps refclocks-------------------------------------------------------.
#   |                                  __      _            _              |
#   |       __ _ _ __  ___   _ __ ___ / _| ___| | ___   ___| | _____       |
#   |      / _` | '_ \/ __| | '__/ _ \ |_ / __| |/ _ \ / __| |/ / __|      |
#   |     | (_| | |_) \__ \ | | |  __/  _| (__| | (_) | (__|   <\__ \      |
#   |      \__, | .__/|___/ |_|  \___|_|  \___|_|\___/ \___|_|\_\___/      |
#   |      |___/|_|                                                        |
#   +----------------------------------------------------------------------+


def discover_lantime_ng_refclock_gps(section: ParsedSection) -> DiscoveryResult:
    for clock in section.values():
        if clock.is_gps:
            yield Service(item=clock.item)


def check_lantime_ng_refclock_gps(
    item: str, params: Mapping[str, Any], section: ParsedSection
) -> CheckResult:
    clock = section.get(item)
    if not clock:
        return

    yield mbg_lantime_ng_generalstate(clock)

    if clock.substate not in ("1", "2"):
        yield Result(state=State.OK, summary="Next leap second: %s" % str(clock.leapsecond_date))

    # Levels for satellites are checked only if we have a substate
    # that indicates that a GPS connection is needed. For the
    # LANTIME M600/MRS the GPS antenna is e.g. optional.
    if clock.substate in ("1", "2", "3", "4", "5", "6", "150"):
        yield from check_levels(
            value=clock.status_a,
            levels_lower=params["levels_lower"],
            render_func=str,
            label=f"Satellites (total: {clock.max_status_a})",
        )


check_plugin_mbg_lantime_ng_refclock_gps = CheckPlugin(
    name="mbg_lantime_ng_refclock_gps",
    service_name="LANTIME Refclock %s",
    sections=["mbg_lantime_ng_refclock"],
    discovery_function=discover_lantime_ng_refclock_gps,
    check_function=check_lantime_ng_refclock_gps,
    check_default_parameters={
        "levels_lower": ("fixed", (3, 3)),
    },
)

# .
#   .--other refclocks-----------------------------------------------------.
#   |                            _   _                                     |
#   |                       ___ | |_| |__   ___ _ __                       |
#   |                      / _ \| __| '_ \ / _ \ '__|                      |
#   |                     | (_) | |_| | | |  __/ |                         |
#   |                      \___/ \__|_| |_|\___|_|                         |
#   |                                                                      |
#   |                         __      _            _                       |
#   |               _ __ ___ / _| ___| | ___   ___| | _____                |
#   |              | '__/ _ \ |_ / __| |/ _ \ / __| |/ / __|               |
#   |              | | |  __/  _| (__| | (_) | (__|   <\__ \               |
#   |              |_|  \___|_|  \___|_|\___/ \___|_|\_\___/               |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_lantime_ng_refclock(section: ParsedSection) -> DiscoveryResult:
    for clock in section.values():
        if not clock.is_gps:  # This will include non-GPS and unknown types
            yield Service(item=clock.item)


def check_lantime_ng_refclock(item: str, section: ParsedSection) -> CheckResult:
    clock = section.get(item)
    if not clock:
        return

    yield mbg_lantime_ng_generalstate(clock)

    if clock.max_status_b != 0:
        field_strength = round(float(clock.status_b) / float(clock.max_status_b) * 100.0)
        yield Result(state=State.OK, summary=f"Field strength: {field_strength}%")
        yield Metric(name="field_strength", value=field_strength)

    # only used for longwave - pzf refclocks
    if clock.max_status_a != 0:
        correlation = round(float(clock.status_a) / float(clock.max_status_a) * 100.0)
        yield Result(state=State.OK, summary=f"Correlation: {correlation}%")
        yield Metric(name="correlation", value=correlation)


def parse_mbg_lantime_ng_refclock(string_table: StringTable) -> ParsedSection:
    return {
        line[0]: RefClock(
            item=line[0],
            clock_type=line[1],
            usage=line[2],
            state=line[3],
            substate=line[4],
            status_a=int(line[5]),
            max_status_a=int(line[6]),
            status_b=int(line[7]),
            max_status_b=int(line[8]),
            info=line[9],
            leapsecond_date=line[10],
        )
        for line in string_table
    }


snmp_section_mbg_lantime_ng_refclock = SimpleSNMPSection(
    name="mbg_lantime_ng_refclock",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.1.2.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    parse_function=parse_mbg_lantime_ng_refclock,
)


check_plugin_mbg_lantime_ng_refclock = CheckPlugin(
    name="mbg_lantime_ng_refclock",
    service_name="LANTIME Refclock %s",
    discovery_function=discover_lantime_ng_refclock,
    check_function=check_lantime_ng_refclock,
)
