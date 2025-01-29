#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.audiocodes.agent_based.sip_calls import (
    check_audiocodes_sip_calls_testable,
    discover_audiocodes_sip_calls,
    IP2Tel,
    METRICS_AND_HEADERS,
    parse_audiocodes_sip_calls,
    SIPCalls,
    Tel2IP,
)


def _parsed_section() -> SIPCalls:
    sip_calls = parse_audiocodes_sip_calls(
        [
            [["1", "2", "3", "5", "1", "0", "10", "0", "0", "2"]],
            [["1", "2", "3", "5", "1", "0", "10", "0", "0", "2"]],
        ]
    )
    assert sip_calls
    return sip_calls


def test_parse_function() -> None:
    assert parse_audiocodes_sip_calls([[], []]) == SIPCalls(tel2ip=None, ip2tel=None)


def test_discovery_function() -> None:
    assert list(discover_audiocodes_sip_calls(_parsed_section())) == [Service()]


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            _parsed_section().tel2ip,
            [
                Result(state=State.OK, summary="Tel2IP Number of Attempted SIP/H323 calls: 0.0/s"),
                Metric("audiocodes_tel2ip_attempted_calls", 0.0),
                Result(
                    state=State.OK,
                    summary="Tel2IP Number of established (connected and voice activated) SIP/H323 calls: 0.0/s",
                ),
                Metric("audiocodes_tel2ip_established_calls", 0.016666666666666666),
                Result(
                    state=State.OK, notice="Tel2IP Number of Destination Busy SIP/H323 calls: 0.0/s"
                ),
                Metric("audiocodes_tel2ip_busy_calls", 0.03333333333333333),
                Result(state=State.OK, notice="Tel2IP Number of No Answer SIP/H323 calls: 0.1/s"),
                Metric("audiocodes_tel2ip_no_answer_calls", 0.06666666666666667),
                Result(
                    state=State.OK,
                    notice="Tel2IP Number of No Route SIP/H323 calls. Most likely to be due to wrong number: 0.0/s",
                ),
                Metric("audiocodes_tel2ip_no_route_calls", 0.0),
                Result(
                    state=State.OK,
                    notice="Tel2IP Number of No capability match between peers on SIP/H323 calls: -0.0/s",
                ),
                Metric("audiocodes_tel2ip_no_match_calls", -0.016666666666666666),
                Result(state=State.OK, notice="Tel2IP Number of failed SIP/H323 calls: 0.1/s"),
                Metric("audiocodes_tel2ip_fail_calls", 0.15),
                Result(
                    state=State.OK, notice="Tel2IP Number of Attempted SIP/H323 fax calls: -0.0/s"
                ),
                Metric("audiocodes_tel2ip_fax_attempted_calls", -0.016666666666666666),
                Result(
                    state=State.OK, notice="Tel2IP Number of SIP/H323 fax success calls: -0.0/s"
                ),
                Metric("audiocodes_tel2ip_fax_success_calls", -0.016666666666666666),
                Result(state=State.OK, notice="Tel2IP Total duration of SIP/H323 calls: 2.00"),
                Metric("audiocodes_tel2ip_total_duration", 2.0),
            ],
            id="Tel2IP",
        ),
        pytest.param(
            _parsed_section().ip2tel,
            [
                Result(state=State.OK, summary="IP2Tel Number of Attempted SIP/H323 calls: 0.0/s"),
                Metric("audiocodes_ip2tel_attempted_calls", 0.0),
                Result(
                    state=State.OK,
                    summary="IP2Tel Number of established (connected and voice activated) SIP/H323 calls: 0.0/s",
                ),
                Metric("audiocodes_ip2tel_established_calls", 0.016666666666666666),
                Result(
                    state=State.OK, notice="IP2Tel Number of Destination Busy SIP/H323 calls: 0.0/s"
                ),
                Metric("audiocodes_ip2tel_busy_calls", 0.03333333333333333),
                Result(state=State.OK, notice="IP2Tel Number of No Answer SIP/H323 calls: 0.1/s"),
                Metric("audiocodes_ip2tel_no_answer_calls", 0.06666666666666667),
                Result(
                    state=State.OK,
                    notice="IP2Tel Number of No Route SIP/H323 calls. Most likely to be due to wrong number: 0.0/s",
                ),
                Metric("audiocodes_ip2tel_no_route_calls", 0.0),
                Result(
                    state=State.OK,
                    notice="IP2Tel Number of No capability match between peers on SIP/H323 calls: -0.0/s",
                ),
                Metric("audiocodes_ip2tel_no_match_calls", -0.016666666666666666),
                Result(state=State.OK, notice="IP2Tel Number of failed SIP/H323 calls: 0.1/s"),
                Metric("audiocodes_ip2tel_fail_calls", 0.15),
                Result(
                    state=State.OK, notice="IP2Tel Number of Attempted SIP/H323 fax calls: -0.0/s"
                ),
                Metric("audiocodes_ip2tel_fax_attempted_calls", -0.016666666666666666),
                Result(
                    state=State.OK, notice="IP2Tel Number of SIP/H323 fax success calls: -0.0/s"
                ),
                Metric("audiocodes_ip2tel_fax_success_calls", -0.016666666666666666),
                Result(state=State.OK, notice="IP2Tel Total duration of SIP/H323 calls: 2.00"),
                Metric("audiocodes_ip2tel_total_duration", 2.0),
            ],
            id="IP2Tel",
        ),
    ],
)
def test_check_function(
    section: Tel2IP | IP2Tel,
    expected: CheckResult,
) -> None:
    now = 1731363504
    value_store = {}
    for metric_name in METRICS_AND_HEADERS:
        value_store[f"{section.metric_prefix}_{metric_name}"] = (now - 60, 1)

    assert (
        list(
            check_audiocodes_sip_calls_testable(
                section=section,
                now=now,
                value_store=value_store,
            ),
        )
        == expected
    )
