#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hitachi.agent_based.hitachi_hus import (
    check_plugin_hitachi_hus_dkc,
    check_plugin_hitachi_hus_dku,
    Section,
    snmp_section_hitachi_hus_dkc,
    snmp_section_hitachi_hus_dku,
)


def _section_dku() -> Section:
    assert (
        section := snmp_section_hitachi_hus_dku.parse_function([[["210221", "1", "1", "1", "1"]]])
    ) is not None
    return section


def test_dku_discovery() -> None:
    assert list(check_plugin_hitachi_hus_dku.discovery_function(_section_dku())) == [
        Service(item="210221")
    ]


def test_dku_check() -> None:
    assert list(check_plugin_hitachi_hus_dku.check_function("210221", _section_dku())) == [
        Result(state=State.OK, summary="Power Supply: no error"),
        Result(state=State.OK, summary="Fan: no error"),
        Result(state=State.OK, summary="Environment: no error"),
        Result(state=State.OK, summary="Drive: no error"),
    ]


def _section_dkc() -> Section:
    assert (
        section := snmp_section_hitachi_hus_dkc.parse_function(
            [[["210221", "1", "1", "1", "1", "1", "1", "1", "1"]]]
        )
    ) is not None
    return section


def test_dkc_discovery() -> None:
    assert list(check_plugin_hitachi_hus_dkc.discovery_function(_section_dkc())) == [
        Service(item="210221")
    ]


def test_dkc_check() -> None:
    assert list(check_plugin_hitachi_hus_dkc.check_function("210221", _section_dkc())) == [
        Result(state=State.OK, summary="Processor: no error"),
        Result(state=State.OK, summary="Internal Bus: no error"),
        Result(state=State.OK, summary="Cache: no error"),
        Result(state=State.OK, summary="Shared Memory: no error"),
        Result(state=State.OK, summary="Power Supply: no error"),
        Result(state=State.OK, summary="Battery: no error"),
        Result(state=State.OK, summary="Fan: no error"),
        Result(state=State.OK, summary="Environment: no error"),
    ]
