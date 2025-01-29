#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterable
from inspect import signature

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.collection.agent_based.ciena_health import (
    _REFERENCES_5142,
    _REFERENCES_5171,
    check_ciena_health,
    parse_ciena_health,
    Section,
    SNMPData,
)
from cmk.plugins.lib.ciena_ces import (
    FanStatus,
    LeoFanStatus,
    LeoPowerSupplyState,
    LeoSystemState,
    PowerSupplyState,
    TceHealthStatus,
)


def test_ciena_health_does_not_provide_metrics():
    """
    You may wonder whether it is ok to change the type returned by check_ciena_health. The answer is
    no. The ciena_health plug-in accumulates a lot of different information (about fans, power
    supplies, etc... and across different devices). The only reason I was able to merge it all, is
    because it can treat all the different OIDs with the same logic. This logic is given by
    _summarize_discrete_snmp_values.

    Do NOT add a metric for rpm fan speed, only because the fan status is found in this check. That
    kind of information is in a different castle.
    """
    assert signature(check_ciena_health).return_annotation == Iterable[Result]


STRING_TABLE_SECTION_CHECK_RESULT_5171 = [
    pytest.param(
        [[["2"]], [["1"]], [["2"], ["2"]], [["2"]], [["1"], ["1"]]],
        [
            SNMPData("memory state(s)", TceHealthStatus, Counter({TceHealthStatus.normal: 1})),
            SNMPData("power supplies", PowerSupplyState, Counter({PowerSupplyState.online: 1})),
            SNMPData("CPU health", TceHealthStatus, Counter({TceHealthStatus.normal: 2})),
            SNMPData("disk(s)", TceHealthStatus, Counter({TceHealthStatus.normal: 1})),
            SNMPData("fan(s)", FanStatus, Counter({FanStatus.ok: 2})),
        ],
        [
            Result(
                state=State.OK,
                summary="1 memory state(s), all normal",
                details="1 memory state(s) | unknown : 0, normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 power supplies, all online",
                details="1 power supplies | online : 1, faulted : 0, offline : 0, uninstalled : 0",
            ),
            Result(
                state=State.OK,
                summary="2 CPU health, all normal",
                details="2 CPU health | unknown : 0, normal : 2, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 disk(s), all normal",
                details="1 disk(s) | unknown : 0, normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="2 fan(s), all ok",
                details="2 fan(s) | ok : 2, pending : 0, rpmwarning : 0, uninstalled : 0, unknown : 0",
            ),
        ],
        id="healthy 5171",
    ),
    pytest.param(
        [[["1"]], [["1"]], [["2"], ["2"]], [["2"]], [["1"], ["1"]]],
        [
            SNMPData("memory state(s)", TceHealthStatus, Counter({TceHealthStatus.unknown: 1})),
            SNMPData("power supplies", PowerSupplyState, Counter({PowerSupplyState.online: 1})),
            SNMPData("CPU health", TceHealthStatus, Counter({TceHealthStatus.normal: 2})),
            SNMPData("disk(s)", TceHealthStatus, Counter({TceHealthStatus.normal: 1})),
            SNMPData("fan(s)", FanStatus, Counter({FanStatus.ok: 2})),
        ],
        [
            Result(
                state=State.CRIT,
                summary="1 memory state(s), some not normal",
                details="1 memory state(s) | unknown : 1, normal : 0, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 power supplies, all online",
                details="1 power supplies | online : 1, faulted : 0, offline : 0, uninstalled : 0",
            ),
            Result(
                state=State.OK,
                summary="2 CPU health, all normal",
                details="2 CPU health | unknown : 0, normal : 2, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 disk(s), all normal",
                details="1 disk(s) | unknown : 0, normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="2 fan(s), all ok",
                details="2 fan(s) | ok : 2, pending : 0, rpmwarning : 0, uninstalled : 0, unknown : 0",
            ),
        ],
        id="unhealthy 5171",
    ),
    pytest.param(
        [[], [["1"], ["1"]], [], [["2"]], [["1"], ["1"]]],
        [
            SNMPData("power supplies", PowerSupplyState, Counter({PowerSupplyState.online: 2})),
            SNMPData("disk(s)", TceHealthStatus, Counter({TceHealthStatus.normal: 1})),
            SNMPData("fan(s)", FanStatus, Counter({FanStatus.ok: 2})),
        ],
        [
            Result(
                state=State.OK,
                summary="2 power supplies, all online",
                details="2 power supplies | online : 2, faulted : 0, offline : 0, uninstalled : 0",
            ),
            Result(
                state=State.OK,
                summary="1 disk(s), all normal",
                details="1 disk(s) | unknown : 0, normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="2 fan(s), all ok",
                details="2 fan(s) | ok : 2, pending : 0, rpmwarning : 0, uninstalled : 0, unknown : 0",
            ),
        ],
        id="missing 5171",
    ),
]


STRING_TABLE_SECTION_CHECK_RESULT_5142 = [
    pytest.param(
        [[["1"]], [["1"], ["1"]], [["1"]], [["1"]], [["1"], ["1"], ["1"]]],
        [
            SNMPData("memory state(s)", LeoSystemState, Counter({LeoSystemState.normal: 1})),
            SNMPData(
                "power supplies", LeoPowerSupplyState, Counter({LeoPowerSupplyState.online: 2})
            ),
            SNMPData("tmpfs", LeoSystemState, Counter({LeoSystemState.normal: 1})),
            SNMPData("sysfs", LeoSystemState, Counter({LeoSystemState.normal: 1})),
            SNMPData("fan(s)", LeoFanStatus, Counter({LeoFanStatus.ok: 3})),
        ],
        [
            Result(
                state=State.OK,
                summary="1 memory state(s), all normal",
                details="1 memory state(s) | normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="2 power supplies, all online",
                details="2 power supplies | online : 2, offline : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 tmpfs, all normal",
                details="1 tmpfs | normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 sysfs, all normal",
                details="1 sysfs | normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="3 fan(s), all ok",
                details="3 fan(s) | ok : 3, pending : 0, failure : 0",
            ),
        ],
        id="healthy 5142",
    ),
    pytest.param(
        [[["2"]], [["1"], ["1"]], [["1"]], [["1"]], [["1"], ["1"], ["1"]]],
        [
            SNMPData("memory state(s)", LeoSystemState, Counter({LeoSystemState.warning: 1})),
            SNMPData(
                "power supplies", LeoPowerSupplyState, Counter({LeoPowerSupplyState.online: 2})
            ),
            SNMPData("tmpfs", LeoSystemState, Counter({LeoSystemState.normal: 1})),
            SNMPData("sysfs", LeoSystemState, Counter({LeoSystemState.normal: 1})),
            SNMPData("fan(s)", LeoFanStatus, Counter({LeoFanStatus.ok: 3})),
        ],
        [
            Result(
                state=State.CRIT,
                summary="1 memory state(s), some not normal",
                details="1 memory state(s) | normal : 0, warning : 1, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="2 power supplies, all online",
                details="2 power supplies | online : 2, offline : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 tmpfs, all normal",
                details="1 tmpfs | normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="1 sysfs, all normal",
                details="1 sysfs | normal : 1, warning : 0, degraded : 0, faulted : 0",
            ),
            Result(
                state=State.OK,
                summary="3 fan(s), all ok",
                details="3 fan(s) | ok : 3, pending : 0, failure : 0",
            ),
        ],
        id="unhealthy 5142",
    ),
]


@pytest.mark.parametrize(
    "_, section, check_result",
    STRING_TABLE_SECTION_CHECK_RESULT_5142 + STRING_TABLE_SECTION_CHECK_RESULT_5171,
)
def test_check_ciena_health_output(
    _: object,
    section: Section,
    check_result: list[Result],
) -> None:
    assert list(check_ciena_health(section)) == check_result


@pytest.mark.parametrize(
    "string_table, section, _",
    STRING_TABLE_SECTION_CHECK_RESULT_5142,
)
def test_parse_ciena_health_5142(
    string_table: list[StringTable],
    section: Section,
    _: object,
) -> None:
    assert parse_ciena_health(_REFERENCES_5142, string_table) == section


@pytest.mark.parametrize(
    "string_table, section, _",
    STRING_TABLE_SECTION_CHECK_RESULT_5171,
)
def test_parse_ciena_health_5171(
    string_table: list[StringTable],
    section: Section,
    _: object,
) -> None:
    assert parse_ciena_health(_REFERENCES_5171, string_table) == section
