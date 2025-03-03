#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableMapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_AUDIOCODES


@dataclass(frozen=True, kw_only=True)
class Tel2IP:
    attempted_calls: int
    established_calls: int
    busy_calls: int
    no_answer_calls: int
    no_route_calls: int
    no_match_calls: int
    fail_calls: int
    fax_attempted_calls: int
    fax_success_calls: int
    total_duration: int

    @property
    def metric_prefix(self) -> str:
        return "tel2ip"

    @property
    def class_name(self) -> str:
        return "Tel2IP"


@dataclass(frozen=True, kw_only=True)
class IP2Tel:
    attempted_calls: int
    established_calls: int
    busy_calls: int
    no_answer_calls: int
    no_route_calls: int
    no_match_calls: int
    fail_calls: int
    fax_attempted_calls: int
    fax_success_calls: int
    total_duration: int

    @property
    def metric_prefix(self) -> str:
        return "ip2tel"

    @property
    def class_name(self) -> str:
        return "IP2Tel"


@dataclass(frozen=True, kw_only=True)
class SIPCalls:
    tel2ip: Tel2IP | None
    ip2tel: IP2Tel | None


METRICS_AND_HEADERS = {
    "attempted_calls": "Number of Attempted SIP/H323 calls",
    "established_calls": "Number of established (connected and voice activated) SIP/H323 calls",
    "busy_calls": "Number of Destination Busy SIP/H323 calls",
    "no_answer_calls": "Number of No Answer SIP/H323 calls",
    "no_route_calls": "Number of No Route SIP/H323 calls. Most likely to be due to wrong number",
    "no_match_calls": "Number of No capability match between peers on SIP/H323 calls",
    "fail_calls": "Number of failed SIP/H323 calls",
    "fax_attempted_calls": "Number of Attempted SIP/H323 fax calls",
    "fax_success_calls": "Number of SIP/H323 fax success calls",
    "total_duration": "Total duration of SIP/H323 calls",
}


def parse_audiocodes_sip_calls(string_table: Sequence[StringTable]) -> SIPCalls | None:
    if not string_table or len(string_table) != 2:
        return None

    try:
        tel2ip_data = string_table[0]
        tel2ip = Tel2IP(
            attempted_calls=int(tel2ip_data[0][0]),
            established_calls=int(tel2ip_data[0][1]),
            busy_calls=int(tel2ip_data[0][2]),
            no_answer_calls=int(tel2ip_data[0][3]),
            no_route_calls=int(tel2ip_data[0][4]),
            no_match_calls=int(tel2ip_data[0][5]),
            fail_calls=int(tel2ip_data[0][6]),
            fax_attempted_calls=int(tel2ip_data[0][7]),
            fax_success_calls=int(tel2ip_data[0][8]),
            total_duration=int(tel2ip_data[0][9]),
        )
    except (ValueError, IndexError):
        tel2ip = None

    try:
        ip2tel_data = string_table[1]
        ip2tel = IP2Tel(
            attempted_calls=int(ip2tel_data[0][0]),
            established_calls=int(ip2tel_data[0][1]),
            busy_calls=int(ip2tel_data[0][2]),
            no_answer_calls=int(ip2tel_data[0][3]),
            no_route_calls=int(ip2tel_data[0][4]),
            no_match_calls=int(ip2tel_data[0][5]),
            fail_calls=int(ip2tel_data[0][6]),
            fax_attempted_calls=int(ip2tel_data[0][7]),
            fax_success_calls=int(ip2tel_data[0][8]),
            total_duration=int(ip2tel_data[0][9]),
        )
    except (ValueError, IndexError):
        ip2tel = None

    return SIPCalls(tel2ip=tel2ip, ip2tel=ip2tel)


snmp_section_audiocodes_alarms = SNMPSection(
    name="audiocodes_sip_calls",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.10.3.1.1.1",
            oids=[
                "1.0",  # AcPerfH323SIPGateway::acPerfTel2IPAttemptedCalls
                "2.0",  # AcPerfH323SIPGateway::acPerfTel2IPEstablishedCalls
                "3.0",  # AcPerfH323SIPGateway::acPerfTel2IPBusyCalls
                "4.0",  # AcPerfH323SIPGateway::acPerfTel2IPNoAnswerCalls
                "5.0",  # AcPerfH323SIPGateway::acPerfTel2IPNoRouteCalls
                "6.0",  # AcPerfH323SIPGateway::acPerfTel2IPNoMatchCalls
                "7.0",  # AcPerfH323SIPGateway::acPerfTel2IPFailCalls
                "8.0",  # AcPerfH323SIPGateway::acPerfTel2IPFaxAttemptedCalls
                "9.0",  # AcPerfH323SIPGateway::acPerfTel2IPFaxSuccessCalls
                "10.0",  # AcPerfH323SIPGateway::acPerfTel2IPTotalDuration
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.10.3.1.1.2",
            oids=[
                "1.0",  # AcPerfH323SIPGateway::acPerfIP2TelAttemptedCalls
                "2.0",  # AcPerfH323SIPGateway::acPerfIP2TelEstablishedCalls
                "3.0",  # AcPerfH323SIPGateway::acPerfIP2TelBusyCalls
                "4.0",  # AcPerfH323SIPGateway::acPerfIP2TelNoAnswerCalls
                "5.0",  # AcPerfH323SIPGateway::acPerfIP2TelNoRouteCalls
                "6.0",  # AcPerfH323SIPGateway::acPerfIP2TelNoMatchCalls
                "7.0",  # AcPerfH323SIPGateway::acPerfIP2TelFailCalls
                "8.0",  # AcPerfH323SIPGateway::acPerfIP2TelFaxAttemptedCalls
                "9.0",  # AcPerfH323SIPGateway::acPerfIP2TelFaxSuccessCalls
                "10.0",  # AcPerfH323SIPGateway::acPerfIP2TelTotalDuration
            ],
        ),
    ],
    parse_function=parse_audiocodes_sip_calls,
)


def discover_audiocodes_sip_calls(section: SIPCalls) -> DiscoveryResult:
    yield Service()


def check_audiocodes_sip_calls(section: SIPCalls) -> CheckResult:
    yield from (
        check_audiocodes_sip_calls_testable(
            section=section.tel2ip, now=time.time(), value_store=get_value_store()
        )
        if section.tel2ip
        else []
    )
    yield from (
        check_audiocodes_sip_calls_testable(
            section=section.ip2tel, now=time.time(), value_store=get_value_store()
        )
        if section.ip2tel
        else []
    )


def check_audiocodes_sip_calls_testable(
    *,
    section: Tel2IP | IP2Tel,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    for key, value in asdict(section).items():
        metric_name = f"audiocodes_{section.metric_prefix}_{key}"
        label = f"{section.class_name} {METRICS_AND_HEADERS[key]}"

        if key == "total_duration":
            yield from check_levels(
                value=value,
                metric_name=metric_name,
                label=label,
                notice_only=True,
                render_func=lambda x: f"{x:.1f}s",
            )
            continue

        rate = get_rate(
            value_store=value_store,
            key=f"{section.metric_prefix}_{key}",
            time=now,
            value=value,
        )
        yield from check_levels(
            value=rate,
            metric_name=metric_name,
            label=label,
            render_func=lambda x: f"{x:.1f}/s",
            notice_only=key not in ("attempted_calls", "established_calls"),
        )


check_plugin_audiocodes_calls = CheckPlugin(
    name="audiocodes_sip_calls",
    service_name="SIP calls",
    discovery_function=discover_audiocodes_sip_calls,
    check_function=check_audiocodes_sip_calls,
)
