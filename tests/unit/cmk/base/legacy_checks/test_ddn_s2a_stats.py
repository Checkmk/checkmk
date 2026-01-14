#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.ddn_s2a_stats import (
    check_ddn_s2a_stats,
    discover_ddn_s2a_stats,
    parse_ddn_s2a_stats,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [("1", {}), ("2", {}), ("3", {}), ("4", {}), ("Total", {})],
        ),
    ],
)
def test_discover_ddn_s2a_stats(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ddn_s2a_stats check."""
    parsed = parse_ddn_s2a_stats(string_table)
    result = list(discover_ddn_s2a_stats(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"total": (5033164800, 5767168000)},
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [
                (0, "Read: 10009.80 MB/s", [("disk_read_throughput", 10496036044.8)]),
                (0, "Write: 35.30 MB/s", [("disk_write_throughput", 37014732.8)]),
                (2, "Total: 10045.10 MB/s (warn/crit at 4800.00/5500.00 MB/s)"),
            ],
        ),
        (
            "2",
            {"total": (5033164800, 5767168000)},
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [
                (0, "Read: 9.80 MB/s", [("disk_read_throughput", 10276044.8)]),
                (0, "Write: 35.50 MB/s", [("disk_write_throughput", 37224448.0)]),
                (0, "Total: 45.30 MB/s"),
            ],
        ),
        (
            "3",
            {"total": (5033164800, 5767168000)},
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [
                (0, "Read: 9.70 MB/s", [("disk_read_throughput", 10171187.2)]),
                (0, "Write: 35.50 MB/s", [("disk_write_throughput", 37224448.0)]),
                (0, "Total: 45.20 MB/s"),
            ],
        ),
        (
            "4",
            {"total": (5033164800, 5767168000)},
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [
                (0, "Read: 9.50 MB/s", [("disk_read_throughput", 9961472.0)]),
                (0, "Write: 35.30 MB/s", [("disk_write_throughput", 37014732.8)]),
                (0, "Total: 44.80 MB/s"),
            ],
        ),
        (
            "Total",
            {"total": (5033164800, 5767168000)},
            [
                [
                    "0@108@OK@0",
                    "of",
                    "0",
                    "parameters",
                    "were",
                    "successful.@All_ports_Read_MBs@100038.8@Read_MBs@10009.8@Read_MBs@9.8@Read_MBs@9.7@Read_MBs@9.5@All_ports_Write_MBs@141.6@Write_MBs@35.3@Write_MBs@35.5@Write_MBs@35.5@Write_MBs@35.3@All_ports_Total_MBs@180.3@Total_MBs@45.2@Total_MBs@45.3@Total_MBs@45.1@Total_MBs@44.8@All_ports_Read_IOs@587@Read_IOs@147@Read_IOs@147@Read_IOs@147@Read_IOs@146@All_ports_Write_IOs@2214@Write_IOs@553@Write_IOs@554@Write_IOs@553@Write_IOs@554@All_ports_Total_IOs@2801@Total_IOs@700@Total_IOs@701@Total_IOs@700@Total_IOs@700@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.6@Read_Hits@99.6@Read_Hits@99.2@All_ports_Prefetch_Hits@49.3@Prefetch_Hits@49.4@Prefetch_Hits@48.5@Prefetch_Hits@49.9@Prefetch_Hits@49.4@All_ports_Prefetches@7.6@Prefetches@4.5@Prefetches@10.9@Prefetches@4.0@Prefetches@10.5@All_ports_Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@Writebacks@100.0@All_ports_Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@Rebuild_MBs@0.0@All_ports_Verify_MBs@0.7@Verify_MBs@0.3@Verify_MBs@0.0@Verify_MBs@0.3@Verify_MBs@0.0@Total_Disk_IOs@752@Read_Disk_IOs@559@Write_Disk_IOs@193@Total_Disk_MBs@187.3@Read_Disk_MBs@24.5@Write_Disk_MBs@162.8@Total_Disk_Pieces@1014658688@Read_Disk_Pieces@810219904@Write_Disk_Pieces@204438752@BDB_Pieces@12941@Skip_Pieces@1737@Piece_map_Reads@551815573@Piece_map_Writes@0@Piece_map_Reads@20021561@Piece_map_Writes@0@Piece_map_Reads@16946297@Piece_map_Writes@0@Piece_map_Reads@1347647@Piece_map_Writes@0@Piece_map_Reads@2909204@Piece_map_Writes@0@Piece_map_Reads@67189@Piece_map_Writes@0@Piece_map_Reads@25551@Piece_map_Writes@0@Piece_map_Reads@28146@Piece_map_Writes@0@Piece_map_Reads@15044@Piece_map_Writes@0@Piece_map_Reads@9938@Piece_map_Writes@0@Piece_map_Reads@9984@Piece_map_Writes@0@Piece_map_Reads@13283@Piece_map_Writes@0@Piece_map_Reads@10382@Piece_map_Writes@0@Piece_map_Reads@14801@Piece_map_Writes@0@Piece_map_Reads@2754@Piece_map_Writes@0@Piece_map_Reads@40494@Piece_map_Writes@0@Cache_Writeback_data@7.6@Rebuild_data@0.0@Verify_data@0.0@Cache_data_locked@0.0@$",
                ],
                ["OVER"],
            ],
            [
                (0, "Read: 100038.80 MB/s", [("disk_read_throughput", 104898284748.8)]),
                (0, "Write: 141.60 MB/s", [("disk_write_throughput", 148478361.6)]),
                (2, "Total: 100180.40 MB/s (warn/crit at 4800.00/5500.00 MB/s)"),
            ],
        ),
    ],
)
def test_check_ddn_s2a_stats(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ddn_s2a_stats check."""
    parsed = parse_ddn_s2a_stats(string_table)
    result = list(check_ddn_s2a_stats(item, params, parsed))
    assert result == expected_results
