#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# grep -r -E ".1.3.6.1.4.1.14525.3.1|.1.3.6.1.4.1.14525.3.3"
# juniper-trpz-1         :.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.14525.3.1.6
# juniper-trpz-2         :.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.14525.3.1.13
# juniper-trpz-wlc-800-1 :.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.14525.3.1.13
# juniper-trpz-wlc-800-2 :.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.14525.3.1.13
# juniper-trpz-wlc-800-3 :.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.14525.3.3.4

import time
from contextlib import suppress
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple, TypedDict

from .agent_based_api.v1 import (
    any_of,
    get_rate,
    get_value_store,
    GetRateError,
    Metric,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    startswith,
)
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

RadioCounters = List[float]

RadioInfo = Dict[str, Tuple[RadioCounters, int, int]]
RadioDict = Dict[str, RadioInfo]


class ApInfo(TypedDict, total=False):
    oid: str
    status: str
    radios: RadioInfo
    passive_node: str
    active_node: str


ApDict = Dict[str, ApInfo]
Section = Tuple[ApDict, RadioDict]

AP_STATES = {
    "1": (state.CRIT, "cleared"),
    "2": (state.WARN, "init"),
    "3": (state.CRIT, "boot started"),
    "4": (state.CRIT, "image downloaded"),
    "5": (state.CRIT, "connect failed"),
    "6": (state.WARN, "configuring"),
    "7": (state.OK, "operational"),
    "10": (state.OK, "redundant"),
    "20": (state.CRIT, "conn outage"),
}


def parse_juniper_trpz_aps_sessions(string_table: List[StringTable]) -> Section:
    """
    >>> aps, radios = parse_juniper_trpz_aps_sessions(
    ...     [[['12.109.103.48.50.49.50.48.51.48.50.54.50', '7', 'ap1'],
    ...       ['12.109.103.48.50.49.50.48.51.51.56.49.53', '10', 'ap2'],
    ...       ['12.109.103.48.50.49.50.48.51.52.53.50.56', '10', 'ap3']],
    ...      [['12.109.103.48.50.49.50.48.51.48.50.54.50.1', '24690029', '16204801769', '651256841', '167276559562', '504451972', '50496155159', '912917', '781', '3611152', '', ''],
    ...       ['12.109.103.48.50.49.50.48.51.48.50.54.50.2', '54719444', '54400648964', '641366904', '158742162014', '121823862', '39011377605', '5533065', '185', '8081876', '', ''],
    ...       ['12.109.103.48.50.49.50.48.51.51.56.49.53.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
    ...       ['12.109.103.48.50.49.50.48.51.51.56.49.53.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
    ...       ['12.109.103.48.50.49.50.48.51.52.53.50.56.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
    ...       ['12.109.103.48.50.49.50.48.51.52.53.50.56.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', '']]]
    ... )
    >>> for name, data in aps.items():
    ...   print("%s: %r" % (name, data))
    ap1: {'oid': '12.109.103.48.50.49.50.48.51.48.50.54.50', 'status': '7'}
    ap2: {'oid': '12.109.103.48.50.49.50.48.51.51.56.49.53', 'status': '10'}
    ap3: {'oid': '12.109.103.48.50.49.50.48.51.52.53.50.56', 'status': '10'}
    >>> for name, data in radios.items():
    ...   print("%s: %r" % (name, data))
    12.109.103.48.50.49.50.48.51.48.50.54.50: {'1': ([24690029, 16204801769, 651256841, 167276559562, 504451972, 50496155159, 912917, 781, 3611152], 0, 0), '2': ([54719444, 54400648964, 641366904, 158742162014, 121823862, 39011377605, 5533065, 185, 8081876], 0, 0)}
    12.109.103.48.50.49.50.48.51.51.56.49.53: {'1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0), '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)}
    12.109.103.48.50.49.50.48.51.52.53.50.56: {'1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0), '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)}
    """

    def to_int(string: str) -> int:
        return int(string) if string else 0

    radios: RadioDict = {}
    for combined_radio_oid, *counters, sessions, noise_floor in string_table[1]:
        for oid, number in (combined_radio_oid.rsplit(".", 1),):
            radios.setdefault(oid, {})[number] = (
                list(map(to_int, counters)),
                to_int(sessions),
                to_int(noise_floor),
            )

    return {
        name.replace("AP-", ""): {
            "oid": oid,
            "status": status,
        }
        for oid, status, name in string_table[0]
    }, radios


def discovery_juniper_trpz_aps_sessions(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section[0])


def _check_common_juniper_trpz_aps_sessions(
    value_store: MutableMapping[str, Any],
    now: float,
    item: str,
    section: Mapping[str, Section],
) -> CheckResult:
    """
    >>> now = time.time()
    >>> vs = {}
    >>> for i in range(2):
    ...   for result in _check_common_juniper_trpz_aps_sessions(vs, now, "ap1", {'': ({
    ...       'ap1': {'oid': '12.109.103.48.50.49.50.48.51.48.50.54.50', 'status': '7'},
    ...       'ap2': {'oid': '12.109.103.48.50.49.50.48.51.51.56.49.53', 'status': '10'},
    ...       'ap3': {'oid': '12.109.103.48.50.49.50.48.51.52.53.50.56', 'status': '10'},
    ...       }, {
    ...       '12.109.103.48.50.49.50.48.51.48.50.54.50': {
    ...           '1': ([24690029, 16204801769, 651256841, 167276559562, 504451972, 50496155159, 912917, 781, 3611152], 0, 0),
    ...           '2': ([54719444, 54400648964, 641366904, 158742162014, 121823862, 39011377605, 5533065, 185, 8081876], 0, 0)},
    ...       '12.109.103.48.50.49.50.48.51.51.56.49.53': {
    ...           '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
    ...           '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)},
    ...       '12.109.103.48.50.49.50.48.51.52.53.50.56': {
    ...           '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
    ...           '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)}
    ...       })}):
    ...     if i: print(result)
    Result(state=<State.OK: 0>, summary='Status: operational')
    Result(state=<State.OK: 0>, summary='Radio 1: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm')
    Result(state=<State.OK: 0>, summary='Radio 2: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm')
    Metric('if_out_unicast', 0.0)
    Metric('if_out_unicast_octets', 0.0)
    Metric('if_out_non_unicast', 0.0)
    Metric('if_out_non_unicast_octets', 0.0)
    Metric('if_in_pkts', 0.0)
    Metric('if_in_octets', 0.0)
    Metric('wlan_physical_errors', 0.0)
    Metric('wlan_resets', 0.0)
    Metric('wlan_retries', 0.0)
    Metric('total_sessions', 0.0)
    Metric('noise_floor', 0.0)
    """
    if all(item not in node_aps for node_aps, _ in section.values()):
        yield Result(state=state.WARN, summary="Access point not reachable")
        return

    item_status, item_active_node, item_passive_node, item_radios = "", "n/A", "n/A", {}
    for node_name, oid, status, node_radios in (  #
        (name, aps[item]["oid"], aps[item]["status"], radios)
        for name, (aps, radios) in section.items()
        if item in aps
    ):
        if item_status != "10":
            item_active_node, item_status = node_name, status
            item_radios = node_radios[oid]
        else:
            item_passive_node = node_name

    state_code, state_string = AP_STATES.get(item_status, (state.UNKNOWN, "unknown"))
    yield Result(
        state=state_code,
        summary="%sStatus: %s"
        % (
            "" if "" in section else ("[%s/%s] " % (item_active_node, item_passive_node)),
            state_string,
        ),
    )

    ap_rates: RadioCounters = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    ap_sessions = 0
    noise_floor_radios = []

    radios: RadioInfo = item_radios
    for radio_number, (counters, sessions, noise_floor) in sorted(radios.items()):
        noise_floor_radios.append(noise_floor)
        ap_sessions += sessions

        radio_rates: RadioCounters = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        for nr, counter in enumerate(counters):
            with suppress(GetRateError):
                radio_rate = get_rate(
                    value_store=value_store,
                    key="%s.%d" % (radio_number, nr),
                    time=now,
                    value=counter,
                )
                radio_rates[nr] = radio_rate
                ap_rates[nr] += radio_rate

        yield Result(
            state=state.OK,
            summary="Radio %s: %s"
            % (
                radio_number,
                ", ".join(
                    (
                        "Input: %s" % render.networkbandwidth(radio_rates[5]),
                        "Output: %s" % render.networkbandwidth(radio_rates[1] + radio_rates[3]),
                        "Errors: %d" % radio_rates[6],
                        "Resets: %d" % radio_rates[7],
                        "Retries: %d" % radio_rates[8],
                        "Sessions: %s" % sessions,
                        "Noise: %s dBm" % noise_floor,
                    )
                ),
            ),
        )

    yield Metric("if_out_unicast", ap_rates[0])
    yield Metric("if_out_unicast_octets", ap_rates[1])
    yield Metric("if_out_non_unicast", ap_rates[2])
    yield Metric("if_out_non_unicast_octets", ap_rates[3])
    yield Metric("if_in_pkts", ap_rates[4])
    yield Metric("if_in_octets", ap_rates[5])
    yield Metric("wlan_physical_errors", ap_rates[6])
    yield Metric("wlan_resets", ap_rates[7])
    yield Metric("wlan_retries", ap_rates[8])
    yield Metric("total_sessions", ap_sessions)

    if noise_floor_radios:
        yield Metric("noise_floor", max(noise_floor_radios))


def check_juniper_trpz_aps_sessions(
    item: str,
    section: Section,
) -> CheckResult:
    yield from _check_common_juniper_trpz_aps_sessions(
        get_value_store(),
        time.time(),
        item,
        {"": section},
    )


def cluster_check_juniper_trpz_aps_sessions(
    item: str,
    section: Mapping[str, Optional[Section]],
) -> CheckResult:
    yield from _check_common_juniper_trpz_aps_sessions(
        get_value_store(),
        time.time(),
        item,
        {k: v for k, v in section.items() if v is not None},
    )


register.snmp_section(
    name="juniper_trpz_aps_sessions",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14525.3.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14525.3.3"),
    ),
    parse_function=parse_juniper_trpz_aps_sessions,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14525.4.5.1.1.2.1",
            oids=[
                OIDEnd(),
                "5",  # trpzApStatApStatusMacApState         -> status of access point
                "8",  # trpzApStatApStatusMacApName          -> name of access point
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.14525.4.5.1.1.10.1",
            oids=[
                OIDEnd(),
                "3",  # trpzApStatRadioOpStatsTxUniPkt       -> unicast packets transmitted
                "4",  # trpzApStatRadioOpStatsTxUniOct       -> octets transmitted in unicast packets
                "5",  # trpzApStatRadioOpStatsTxMultiPkt     -> multicast packets transmitted
                "6",  # trpzApStatRadioOpStatsTxMultiOct     -> octets transmitted in multicast packets
                "7",  # trpzApStatRadioOpStatsRxPkt          -> packets received
                "8",  # trpzApStatRadioOpStatsRxOctet        -> octets received
                "11",  # trpzApStatRadioOpStatsPhyErr         -> nr. physical errors occurred
                "12",  # trpzApStatRadioOpStatsResetCount     -> nr. reset operations
                "14",  # trpzApStatRadioOpStatsRxRetriesCount -> nr. transmission retries
                "15",  # trpzApStatRadioOpStatsUserSessions   -> current client sessions
                "16",  # trpzApStatRadioOpStatsNoiseFloor     -> noise floor (dBm)
            ],
        ),
    ],
)

register.check_plugin(
    name="juniper_trpz_aps_sessions",
    service_name="Access Point %s",
    discovery_function=discovery_juniper_trpz_aps_sessions,
    check_function=check_juniper_trpz_aps_sessions,
    cluster_check_function=cluster_check_juniper_trpz_aps_sessions,
)
