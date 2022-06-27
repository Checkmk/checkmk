#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.cisco_asa_failover import (
    check_cisco_asa_failover,
    discovery_cisco_asa_failover,
    parse_cisco_asa_failover,
    Section,
)

_CHECK_PARAMS = {
    "primary": "active",
    "secondary": "standby",
    "failover_state": 1,
    "failover_link_state": 2,
    "not_active_standby_state": 1,
}


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [
                [
                    "Failover LAN Interface",
                    "2",
                    "ClusterLink Port-channel4 (system)",
                ],
                [
                    "Primary unit (this device)",
                    "9",
                    "Active unit",
                ],
                [
                    "Secondary unit",
                    "10",
                    "Standby unit",
                ],
            ],
            Section(
                local_role="primary",
                local_status="9",
                local_status_detail="Active unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="10",
            ),
            id="Parse: Primary unit == Active unit",
        ),
        pytest.param(
            [
                [
                    "Failover LAN Interface",
                    "3",
                    "not Configured",
                ],
                [
                    "Primary unit (this device)",
                    "3",
                    "Failover Off",
                ],
                [
                    "Secondary unit",
                    "3",
                    "Failover Off",
                ],
            ],
            None,
            id="Parse: failover off/not configured",
        ),
    ],
)
def test_cisco_asa_failover_parse(string_table, expected) -> None:
    assert parse_cisco_asa_failover(string_table) == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            Section(
                local_role="primary",
                local_status="9",
                local_status_detail="Active unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="10",
            ),
            [Service()],
            id="Discovery: Primary unit == Active unit",
        ),
    ],
)
def test_cisco_asa_failover_discover(section, expected) -> None:
    assert list(discovery_cisco_asa_failover(section)) == expected


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            _CHECK_PARAMS,
            Section(
                local_role="primary",
                local_status="9",
                local_status_detail="Active unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="10",
            ),
            [
                Result(
                    state=State.OK,
                    summary="Device (primary) is the Active unit",
                ),
            ],
            id="Check: local unit == Primary unit == Active unit",
        ),
        pytest.param(
            _CHECK_PARAMS,
            Section(
                local_role="primary",
                local_status="10",
                local_status_detail="Standby unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="9",
            ),
            [
                Result(
                    state=State.OK,
                    summary="Device (primary) is the Standby unit",
                ),
                Result(
                    state=State.WARN,
                    summary="(The primary device should be active)",
                ),
            ],
            id="Check: local unit == Primary unit == Standby unit",
        ),
        pytest.param(
            _CHECK_PARAMS,
            Section(
                local_role="primary",
                local_status="8",
                local_status_detail="Backup unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="10",
            ),
            [
                Result(
                    state=State.OK,
                    summary="Device (primary) is the Backup unit",
                ),
                Result(
                    state=State.WARN,
                    summary="(The primary device should be active)",
                ),
                Result(
                    state=State.WARN,
                    summary="Unhandled state backup reported",
                ),
            ],
            id="Check: local unit not active/standby",
        ),
        pytest.param(
            _CHECK_PARAMS,
            Section(
                local_role="primary",
                local_status="9",
                local_status_detail="Active unit",
                failover_link_status="3",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="10",
            ),
            [
                Result(
                    state=State.OK,
                    summary="Device (primary) is the Active unit",
                ),
                Result(
                    state=State.CRIT,
                    summary="Failover link ClusterLink Port-channel4 (system) state is down",
                ),
            ],
            id="Check: Failover link not up",
        ),
        pytest.param(
            _CHECK_PARAMS,
            Section(
                local_role="primary",
                local_status="9",
                local_status_detail="Active unit",
                failover_link_status="2",
                failover_link_name="ClusterLink Port-channel4 (system)",
                remote_status="8",
            ),
            [
                Result(
                    state=State.OK,
                    summary="Device (primary) is the Active unit",
                ),
                Result(
                    state=State.WARN,
                    summary="Unhandled state backup for remote device reported",
                ),
            ],
            id="Check: Remote unit == not active/standby",
        ),
    ],
)
def test_cisco_asa_failover(params, section, expected) -> None:
    result = check_cisco_asa_failover(params, section)
    assert list(result) == expected
