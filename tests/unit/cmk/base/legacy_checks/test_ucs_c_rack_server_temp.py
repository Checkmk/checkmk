#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.ucs_c_rack_server_temp import (
    check_ucs_c_rack_server_temp,
    discover_ucs_c_rack_server_temp,
    parse_ucs_c_rack_server_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [
                ("Rack Unit 1 CPU 1", {}),
                ("Rack Unit 1 CPU 2", {}),
                ("Rack Unit 1 Memory Array 1 Memory DIMM 1", {}),
                ("Rack Unit 1 Memory Array 1 Memory DIMM 2", {}),
                ("Rack Unit 1 Motherboard", {}),
                ("Rack Unit 2 Motherboard", {}),
            ],
        ),
    ],
)
def test_discover_ucs_c_rack_server_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_c_rack_server_temp check."""
    parsed = parse_ucs_c_rack_server_temp(string_table)
    result = list(discover_ucs_c_rack_server_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Rack Unit 1 CPU 1",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "58.4 °C", [("temp", 58.4, None, None)])],
        ),
        (
            "Rack Unit 1 CPU 2",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "60.4 °C", [("temp", 60.4, None, None)])],
        ),
        (
            "Rack Unit 1 Memory Array 1 Memory DIMM 1",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "40.4 °C", [("temp", 40.4, None, None)])],
        ),
        (
            "Rack Unit 1 Memory Array 1 Memory DIMM 2",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "61.4 °C", [("temp", 61.4, None, None)])],
        ),
        (
            "Rack Unit 1 Motherboard",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "50.0 °C", [("temp", 50.0, None, None)])],
        ),
        (
            "Rack Unit 2 Motherboard",
            {},
            [
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-1/env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 58.4",
                ],
                [
                    "processorEnvStats",
                    "dn sys/rack-unit-1/board/cpu-2/env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 60.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
                    "id 1",
                    "description blalub",
                    "temperature 40.4",
                ],
                [
                    "memoryUnitEnvStats",
                    "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
                    "id 2",
                    "description blalub",
                    "temperature 61.4",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-1/board/temp-stats",
                    "ambientTemp 40.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
                [
                    "computeRackUnitMbTempStats",
                    "dn sys/rack-unit-2/board/temp-stats",
                    "ambientTemp 60.0",
                    "frontTemp 50.0",
                    "ioh1Temp 50.0",
                    "ioh2Temp 50.0",
                    "rearTemp 50.0",
                ],
            ],
            [(0, "50.0 °C", [("temp", 50.0, None, None)])],
        ),
    ],
)
def test_check_ucs_c_rack_server_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_c_rack_server_temp check."""
    parsed = parse_ucs_c_rack_server_temp(string_table)
    result = list(check_ucs_c_rack_server_temp(item, params, parsed))
    assert result == expected_results
