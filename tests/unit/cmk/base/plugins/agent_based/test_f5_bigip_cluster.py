#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.f5_bigip_cluster import (
    check_f5_bigip_config_sync_pre_v11,
    check_f5_bigip_config_sync_v11_plus,
    CONFIG_SYNC_DEFAULT_PARAMETERS,
    parse_f5_bigip_config_sync_pre_v11,
    parse_f5_bigip_config_sync_v11_plus,
    State,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [[["-1 - uninitialized or disabled config state"]]],
            ("-1", "uninitialized or disabled config state"),
        ),
        (
            [[["3 - Config modified on both systems, manual intervention required"]]],
            ("3", "Config modified on both systems, manual intervention required"),
        ),
        ([[["0 - Synchronized"]]], ("0", "Synchronized")),
    ],
)
def test_parse_f5_bigip_config_sync_pre_v11(string_table, expected_parsed_data):
    assert parse_f5_bigip_config_sync_pre_v11(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[["2", "Changes Pending"]]], ("2", "Changes Pending")),
        ([[["3", "In Sync"]]], ("3", "In Sync")),
        ([[["6", "Standalone"]]], ("6", "Standalone")),
    ],
)
def test_parse_f5_bigip_config_sync_v11_plus(string_table, expected_parsed_data):
    assert parse_f5_bigip_config_sync_v11_plus(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,result",
    [
        (
            ("-1", "uninitialized or disabled config state"),
            [Result(state=state.CRIT, summary="uninitialized or disabled config state")],
        ),
        (
            ("3", "Config modified on both systems, manual intervention required"),
            [
                Result(
                    state=state.CRIT,
                    summary="Config modified on both systems, manual intervention required",
                )
            ],
        ),
        (
            ("0", "Synchronized"),
            [Result(state=state.OK, summary="Synchronized")],
        ),
    ],
)
def test_check_f5_bigip_config_sync_pre_v11(section, result):
    assert list(check_f5_bigip_config_sync_pre_v11(State(*section))) == result


@pytest.mark.parametrize(
    "section,result",
    [
        (
            ("2", "Changes Pending"),
            [Result(state=state.WARN, summary="Need Manual Sync - Changes Pending")],
        ),
        (
            ("3", "In Sync"),
            [Result(state=state.OK, summary="In Sync")],
        ),
        (
            ("6", "Standalone"),
            [Result(state=state.CRIT, summary="Standalone")],
        ),
    ],
)
def test_check_f5_bigip_config_sync_v11_plus(section, result):
    assert (
        list(
            check_f5_bigip_config_sync_v11_plus(
                CONFIG_SYNC_DEFAULT_PARAMETERS,
                State(*section),
            )
        )
        == result
    )
