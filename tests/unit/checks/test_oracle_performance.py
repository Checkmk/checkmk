#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Tuple

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

import cmk


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "Oracle DB",
            {
                "dbtime": [("oracle_db_cpu", (1.0, 2.0))],
            },
            {
                "Oracle DB": {
                    "sys_time_model": {"DB CPU": 1000000, "DB time": 1000000},
                }
            },
            [
                Result(state=State.OK, summary="DB Time: 0.00 1/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00 1/s"),
                Metric("oracle_db_cpu", 0.0, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00 1/s"),
                Metric("oracle_db_wait_time", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_dbtime(
    fix_register: FixRegister,
    monkeypatch,
    item: str,
    params: Mapping[str, Sequence[Tuple[str, Tuple[float, float]]]],
    parsed,
    expected_result: Sequence[Tuple[str, Mapping]],
):
    monkeypatch.setattr(cmk.base.item_state, "raise_counter_wrap", lambda: None)

    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance_dbtime")]
    results = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert results == expected_result


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "Oracle DB",
            {
                "memory": [("oracle_sga_size", (1, 2))],
            },
            {
                "Oracle DB": {
                    "SGA_info": {
                        "Maximum SGA Size": 34359738368,
                    },
                    "PGA_info": {
                        "total PGA allocated": [2561432576, None],
                    },
                }
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Maximum SGA Size: 32.0 GiB (warn/crit at 1 B/2 B)",
                ),
                Metric("oracle_sga_size", 34359738368.0, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="total PGA allocated: 2.39 GiB"),
                Metric("oracle_pga_total_pga_allocated", 2561432576.0),
            ],
        )
    ],
)
def test_check_oracle_performance_memory(
    fix_register: FixRegister,
    item: str,
    params: Mapping[str, Sequence[Tuple[str, Tuple[float, float]]]],
    parsed,
    expected_result: Sequence[Tuple[str, Mapping]],
):
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance_memory")]
    results = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert results == expected_result


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "Oracle DB",
            {
                "memory": [("oracle_sga_size", (1, 2))],
            },
            {
                "Oracle DB": {
                    "iostat_file": {
                        "Archive Log Backup": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    }
                }
            },
            [
                Metric("oracle_ios_f_archive_log_backup_s_r", 0.0),
                Metric("oracle_ios_f_archive_log_backup_l_r", 0.0),
                Metric("oracle_ios_f_archive_log_backup_s_w", 0.0),
                Metric("oracle_ios_f_archive_log_backup_l_w", 0.0),
                Result(state=State.OK, summary="Small Reads: 0.00 1/s"),
                Metric("oracle_ios_f_total_s_r", 0.0),
                Result(state=State.OK, summary="Large Reads: 0.00 1/s"),
                Metric("oracle_ios_f_total_l_r", 0.0),
                Result(state=State.OK, summary="Small Writes: 0.00 1/s"),
                Metric("oracle_ios_f_total_s_w", 0.0),
                Result(state=State.OK, summary="Large Writes: 0.00 1/s"),
                Metric("oracle_ios_f_total_l_w", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_iostat_ios(
    fix_register: FixRegister,
    item: str,
    params: Mapping[str, Sequence[Tuple[str, Tuple[float, float]]]],
    parsed,
    expected_result: Sequence[Tuple[str, Mapping]],
):
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance_iostat_ios")]
    results = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert results == expected_result


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "Oracle DB",
            {
                "waitclasses": [("oracle_wait_class_total", (1.0, 3.0))],
            },
            {
                "Oracle DB": {
                    "sys_wait_class": {
                        "Administrative": [207484198, 36421528, 162, 118],
                    },
                }
            },
            [
                Metric("oracle_wait_class_administrative_waited", 0.0),
                Metric("oracle_wait_class_administrative_waited_fg", 0.0),
                Result(state=State.OK, summary="Total waited: 0.00 1/s"),
                Metric("oracle_wait_class_total", 0.0, levels=(1.0, 3.0)),
                Result(state=State.OK, summary="Total waited (FG): 0.00 1/s"),
                Metric("oracle_wait_class_total_fg", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_waitclasses(
    fix_register: FixRegister,
    monkeypatch,
    item: str,
    params: Mapping[str, Sequence[Tuple[str, Tuple[float, float]]]],
    parsed,
    expected_result: Sequence[Tuple[str, Mapping]],
):
    monkeypatch.setattr(cmk.base.item_state, "raise_counter_wrap", lambda: None)

    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance_waitclasses")]
    results = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert results == expected_result
