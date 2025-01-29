#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.oracle.agent_based import oracle_performance_check as opc
from cmk.plugins.oracle.agent_based.liboracle import SectionPerformance
from cmk.plugins.oracle.agent_based.oracle_performance_inventory import inventory_oracle_performance
from cmk.plugins.oracle.agent_based.oracle_performance_section import parse_oracle_performance

_AGENT_OUTPUT_1 = [
    ["TWH", "sys_time_model", "DB CPU", "14826"],
    ["TWH", "sys_time_model", "DB time", "69830"],
    [
        "TWH",
        "buffer_pool_statistics",
        "DEFAULT",
        "63743116",
        "55914822",
        "1059719411",
        "21386319",
        "1506816",
        "0",
        "1631907",
    ],
    [
        "TWH",
        "librarycache",
        "SQL AREA",
        "248642",
        "227658",
        "10643092",
        "10582899",
        "13830",
        "14665",
    ],
    ["TWH", "librarycache", "TABLE/PROCEDURE", "99440", "90692", "467944", "453367", "838", "3"],
]
_AGENT_OUTPUT_2 = [
    ["SGP", "sys_time_model", "DB CPU", "55555899"],
    ["SGP", "sys_time_model", "DB time", "60435096"],
    ["SGP", "SGA_info", "Redo Buffers", "14655488"],
    ["SGP", "SGA_info", "Buffer Cache Size", "3875536896"],
    ["SGP", "SGA_info", "Shared Pool Size", "5385486336"],
    ["SGP", "SGA_info", "Large Pool Size", "33554432"],
    ["SGP", "SGA_info", "Java Pool Size", "67108864"],
    ["SGP", "SGA_info", "Streams Pool Size", "0"],
    ["SGP", "SGA_info", "Granule Size", "16777216"],
    ["SGP", "SGA_info", "Maximum SGA Size", "13119782912"],
    ["SGP", "SGA_info", "Startup overhead in Shared Pool", "218103808"],
    ["SGP", "SGA_info", "Free SGA Memory Available", "3187671040"],
    ["SGP", "librarycache", "JAVA RESOURCE", "2", "0", "2", "0", "0", "0"],
    ["SGP", "librarycache", "JAVA DATA", "18", "5", "676", "663", "0", "0"],
]


@pytest.fixture(name="get_rate_zero", scope="function")
def _get_rate_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opc, "get_rate", lambda *a, **kw: 0.0)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT_1,
            [Service(item="TWH", parameters={"check_dbtime": True, "check_memory": True})],
        ),
        (
            _AGENT_OUTPUT_2,
            [Service(item="SGP", parameters={"check_dbtime": True, "check_memory": True})],
        ),
    ],
)
def test_discover_oracle_performance(
    string_table: StringTable, expected_result: Sequence[Service]
) -> None:
    section = parse_oracle_performance(string_table)
    assert sorted(opc.discover_oracle_performance({}, section)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT_1,
            "TWH",
            [
                Result(state=State.OK, summary="DB Time: 0.00/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00/s"),
                Metric("oracle_db_cpu", 0.0),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00/s"),
                Metric("oracle_db_wait_time", 0.0),
                Result(state=State.OK, summary="Buffer hit ratio: 98.1%"),
                Metric("oracle_buffer_hit_ratio", 98.096392315184),
                Result(state=State.OK, summary="Library cache hit ratio: 99.3%"),
                Metric("oracle_library_cache_hit_ratio", 99.32706545096245),
                Metric("oracle_buffer_busy_wait", 0.0),
                Metric("oracle_consistent_gets", 0.0),
                Metric("oracle_db_block_change", 0.0),
                Metric("oracle_db_block_gets", 0.0),
                Metric("oracle_free_buffer_wait", 0.0),
                Metric("oracle_physical_reads", 0.0),
                Metric("oracle_physical_writes", 0.0),
                Metric("oracle_pin_hits_sum", 0.0),
                Metric("oracle_pins_sum", 0.0),
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SGP",
            [
                Result(state=State.OK, summary="DB Time: 0.00/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00/s"),
                Metric("oracle_db_cpu", 0.0),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00/s"),
                Metric("oracle_db_wait_time", 0.0),
                Result(state=State.OK, summary="Maximum SGA Size: 12.2 GiB"),
                Result(state=State.OK, summary="Buffer Cache Size: 3.61 GiB"),
                Result(state=State.OK, summary="Shared Pool Size: 5.02 GiB"),
                Result(state=State.OK, summary="Redo Buffers: 14.0 MiB"),
                Result(state=State.OK, summary="Java Pool Size: 64.0 MiB"),
                Result(state=State.OK, summary="Large Pool Size: 32.0 MiB"),
                Result(state=State.OK, summary="Streams Pool Size: 0 B"),
                Result(state=State.OK, summary="Library cache hit ratio: 97.8%"),
                Metric("oracle_library_cache_hit_ratio", 97.78761061946902),
                Metric("oracle_pin_hits_sum", 0.0),
                Metric("oracle_pins_sum", 0.0),
                Metric("oracle_sga_buffer_cache", 3875536896.0),
                Metric("oracle_sga_java_pool", 67108864.0),
                Metric("oracle_sga_large_pool", 33554432.0),
                Metric("oracle_sga_redo_buffer", 14655488.0),
                Metric("oracle_sga_shared_pool", 5385486336.0),
                Metric("oracle_sga_size", 13119782912.0),
                Metric("oracle_sga_streams_pool", 0.0),
            ],
        ),
    ],
)
def test_check_oracle_performance(
    get_rate_zero: None, string_table: StringTable, item: str, expected_result: CheckResult
) -> None:
    section = parse_oracle_performance(string_table)
    assert (
        list(
            opc.check_oracle_performance(
                item, {"check_dbtime": True, "check_memory": True}, section
            )
        )
        == expected_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            _AGENT_OUTPUT_1,
            [],
        ),
        (
            _AGENT_OUTPUT_2,
            [
                TableRow(
                    path=["software", "applications", "oracle", "sga"],
                    key_columns={
                        "sid": "SGP",
                    },
                    inventory_columns={},
                    status_columns={
                        "fixed_size": None,
                        "max_size": 13119782912,
                        "redo_buffer": 14655488,
                        "buf_cache_size": 3875536896,
                        "in_mem_area_size": None,
                        "shared_pool_size": 5385486336,
                        "large_pool_size": 33554432,
                        "java_pool_size": 67108864,
                        "streams_pool_size": 0,
                        "shared_io_pool_size": None,
                        "data_trans_cache_size": None,
                        "granule_size": 16777216,
                        "start_oh_shared_pool": 218103808,
                        "free_mem_avail": 3187671040,
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_performance(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    assert (
        list(inventory_oracle_performance(parse_oracle_performance(string_table)))
        == expected_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Oracle DB",
            {
                "dbtime": [("oracle_db_cpu", ("fixed", (1.0, 2.0)))],
            },
            {
                "Oracle DB": {
                    "sys_time_model": {"DB CPU": 1000000, "DB time": 1000000},
                }
            },
            [
                Result(state=State.OK, summary="DB Time: 0.00/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00/s"),
                Metric("oracle_db_cpu", 0.0, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00/s"),
                Metric("oracle_db_wait_time", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_dbtime(
    get_rate_zero: None,
    item: str,
    params: Mapping[str, Sequence[tuple[str, tuple[float, float]]]],
    section: SectionPerformance,
    expected_result: CheckResult,
) -> None:
    assert list(opc.check_oracle_performance_dbtime(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Oracle DB",
            {
                "memory": [("oracle_sga_size", ("fixed", (1, 2)))],
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
    item: str,
    params: Mapping[str, Sequence[tuple[str, tuple[float, float]]]],
    section: SectionPerformance,
    expected_result: CheckResult,
) -> None:
    assert list(opc.check_oracle_performance_memory(item, params, section)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Oracle DB",
            {
                "memory": [("oracle_sga_size", ("fixed", (1, 2)))],
            },
            {
                "Oracle DB": {
                    "iostat_file": {
                        "Archive Log Backup": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    }
                }
            },
            [
                Result(state=State.OK, notice="Archive Log Backup Small Reads: 0.00/s"),
                Metric("oracle_ios_f_archive_log_backup_s_r", 0.0),
                Result(state=State.OK, notice="Archive Log Backup Large Reads: 0.00/s"),
                Metric("oracle_ios_f_archive_log_backup_l_r", 0.0),
                Result(state=State.OK, notice="Archive Log Backup Small Writes: 0.00/s"),
                Metric("oracle_ios_f_archive_log_backup_s_w", 0.0),
                Result(state=State.OK, notice="Archive Log Backup Large Writes: 0.00/s"),
                Metric("oracle_ios_f_archive_log_backup_l_w", 0.0),
                Result(state=State.OK, summary="Small Reads: 0.00/s"),
                Metric("oracle_ios_f_total_s_r", 0.0),
                Result(state=State.OK, summary="Large Reads: 0.00/s"),
                Metric("oracle_ios_f_total_l_r", 0.0),
                Result(state=State.OK, summary="Small Writes: 0.00/s"),
                Metric("oracle_ios_f_total_s_w", 0.0),
                Result(state=State.OK, summary="Large Writes: 0.00/s"),
                Metric("oracle_ios_f_total_l_w", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_iostat_ios(
    get_rate_zero: None,
    item: str,
    params: Mapping[str, Sequence[tuple[str, tuple[float, float]]]],
    section: SectionPerformance,
    expected_result: CheckResult,
) -> None:
    assert list(opc.check_oracle_performance_iostat_ios(item, params, section)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Oracle DB",
            {
                "waitclasses": [("oracle_wait_class_total", ("fixed", (1.0, 3.0)))],
            },
            {
                "Oracle DB": {
                    "sys_wait_class": {
                        "Administrative": [207484198, 36421528, 162, 118],
                    },
                }
            },
            [
                Result(state=State.OK, notice="Administrative wait class: 0.00/s"),
                Metric("oracle_wait_class_administrative_waited", 0.0),
                Result(state=State.OK, notice="Administrative wait class (FG): 0.00/s"),
                Metric("oracle_wait_class_administrative_waited_fg", 0.0),
                Result(state=State.OK, summary="Total waited: 0.00/s"),
                Metric("oracle_wait_class_total", 0.0, levels=(1.0, 3.0)),
                Result(state=State.OK, summary="Total waited (FG): 0.00/s"),
                Metric("oracle_wait_class_total_fg", 0.0),
            ],
        )
    ],
)
def test_check_oracle_performance_waitclasses(
    get_rate_zero: None,
    item: str,
    params: Mapping[str, Sequence[tuple[str, tuple[float, float]]]],
    section: SectionPerformance,
    expected_result: CheckResult,
) -> None:
    assert list(opc.check_oracle_performance_waitclasses(item, params, section)) == expected_result
