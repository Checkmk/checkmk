#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.palo_alto_state import (
    _STATE_MAPPING_DEFAULT,
    check,
    discover,
    parse,
    SectionPaloAlto,
)

_Section = SectionPaloAlto(
    firmware_version="5.0.6",
    ha_local_state="suspended",
    ha_peer_state="unknown",
    ha_mode="active-active",
)
_Section2 = SectionPaloAlto(
    firmware_version="5.0.6",
    ha_local_state="non_functional",
    ha_peer_state="active",
    ha_mode="active-passive",
)
_Section3 = SectionPaloAlto(
    firmware_version="5.0.6",
    ha_local_state="disabled",
    ha_peer_state="unknown",
    ha_mode="disabled",
)
_Section4 = SectionPaloAlto(
    firmware_version="5.0.6",
    ha_local_state="initial",
    ha_peer_state="initial",
    ha_mode="active-passive",
)


def test_parse() -> None:
    info: StringTable = [["5.0.6", "suspended", "unknown", "active-active"]]
    assert parse(info) == _Section


def test_discover() -> None:
    assert list(discover(_Section)) == [Service()]


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            _Section,
            [
                Result(state=State.OK, summary="Firmware Version: 5.0.6"),
                Result(state=State.OK, summary="HA mode: active-active"),
                Result(state=State.CRIT, summary="HA local state: suspended"),
                Result(state=State.UNKNOWN, notice="HA peer state: unknown"),
            ],
            id="local state suspended",
        ),
        pytest.param(
            _Section2,
            [
                Result(state=State.OK, summary="Firmware Version: 5.0.6"),
                Result(state=State.OK, summary="HA mode: active-passive"),
                Result(state=State.CRIT, summary="HA local state: non_functional"),
                Result(state=State.OK, notice="HA peer state: active"),
            ],
            id="local state non_functional",
        ),
        pytest.param(
            _Section3,
            [
                Result(state=State.OK, summary="Firmware Version: 5.0.6"),
                Result(state=State.OK, summary="HA mode: disabled"),
                Result(state=State.OK, summary="HA local state: disabled"),
                Result(state=State.OK, notice="HA peer state: unknown"),
            ],
            id="mode disabled",
        ),
        pytest.param(
            _Section4,
            [
                Result(state=State.OK, summary="Firmware Version: 5.0.6"),
                Result(state=State.OK, summary="HA mode: active-passive"),
                Result(state=State.WARN, summary="HA local state: initial"),
                Result(state=State.WARN, notice="HA peer state: initial"),
            ],
            id="local and peer state initial",
        ),
    ],
)
def test_check(section: SectionPaloAlto, expected_result: Sequence[Result]) -> None:
    assert list(check(_STATE_MAPPING_DEFAULT, section)) == expected_result


@pytest.mark.xfail(
    strict=True,
    reason="Crash report 498526ac-a151-11f1-8fd9-00155d0229c7: KeyError: 'ha_local_state_initial'",
)
def test_check_state_missing_from_mapping() -> None:
    # A device reporting an HA state the mapping does not cover. Observed with a
    # rule saved before "initial" was added to the ruleset, and reproducible
    # whenever PAN-OS reports a state Checkmk does not know yet.
    mapping = {k: v for k, v in _STATE_MAPPING_DEFAULT.items() if not k.endswith("_initial")}
    assert list(check(mapping, _Section4)) == [
        Result(state=State.OK, summary="Firmware Version: 5.0.6"),
        Result(state=State.OK, summary="HA mode: active-passive"),
        Result(
            state=State.UNKNOWN,
            summary="HA local state: initial (no monitoring state defined for this value)",
        ),
        Result(
            state=State.UNKNOWN,
            notice="HA peer state: initial (no monitoring state defined for this value)",
        ),
    ]
