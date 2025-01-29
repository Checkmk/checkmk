#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_pcie_flash_modules import (
    check_fjdarye_pcie_flash_modules,
    discover_fjdarye_pcie_flash_modules,
    parse_fjdarye_pcie_flash_modules,
    PCIeFlashModule,
    PCIeFlashModuleSection,
)


@pytest.mark.parametrize(
    "string_table, parse_result",
    [
        pytest.param(
            [
                [
                    ["1996492800", "1", "49"],
                    ["1996492801", "4", "-1"],
                    ["1996492802", "4", "-1"],
                ],
                [],
            ],
            {
                "1996492800": PCIeFlashModule("1996492800", "1", 49.00),
                "1996492801": PCIeFlashModule("1996492801", "4", -1.00),
                "1996492802": PCIeFlashModule("1996492802", "4", -1.00),
            },
            id="The input is parsed into a dictionary, that contains information about the modules id, status and health lifetime.",
        ),
        pytest.param(
            [],
            {},
            id="If the input is empty, nothing is parsed.",
        ),
    ],
)
def test_parse_fjdarye_pcie_flash_modules(
    string_table: Sequence[StringTable],
    parse_result: PCIeFlashModuleSection,
) -> None:
    assert parse_fjdarye_pcie_flash_modules(string_table=string_table) == parse_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {
                "1996492800": PCIeFlashModule("1996492800", "1", 49.00),
                "1996492801": PCIeFlashModule("1996492801", "4", -1.00),
                "1996492802": PCIeFlashModule("1996492802", "4", -1.00),
            },
            [Service(item="1996492800")],
            id="A service is discovered for all PFMs that don't have a status of 4.",
        ),
        pytest.param(
            {
                "1996492801": PCIeFlashModule("1996492801", "4", -1.00),
                "1996492802": PCIeFlashModule("1996492802", "4", -1.00),
            },
            [],
            id="If the status of all PFMs is 4, no service is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the info is empty, no service is discovered.",
        ),
    ],
)
def test_discover_fjdarye_pcie_flash_modules(
    section: PCIeFlashModuleSection,
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_fjdarye_pcie_flash_modules(section)) == discovery_result


@pytest.mark.parametrize(
    "item, params, section, check_result",
    [
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "1", 49.00)},
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 1 or 5, the result of the first check result is OK with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "2", 49.00)},
            [
                Result(state=State.CRIT, summary="Status: alarm"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 2 or 4, the result of the first check result is CRIT with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "3", 49.00)},
            [
                Result(state=State.WARN, summary="Status: warning"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 3, the result of the first check result is WARN with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "6", 49.00)},
            [
                Result(state=State.UNKNOWN, summary="Status: undefined"),
                Result(state=State.OK, summary="Health lifetime: 49.00%"),
            ],
            id="If the status of the PFM is 6, the result of the first check result is UNKNOWN with a description of the status.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "1", 19.00)},
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.WARN,
                    summary="Health lifetime: 19.00% (warn/crit below 20.00%/15.00%)",
                ),
            ],
            id="If the health lifetime of the PFM is below the WARN level, the result of the second check result is WARN with a description of the thresholds.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "1", 13.00)},
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.CRIT,
                    summary="Health lifetime: 13.00% (warn/crit below 20.00%/15.00%)",
                ),
            ],
            id="If the health lifetime of the PFM is below the CRIT level, the result of the second check result is CRIT with a description of the thresholds.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "1", -1.00)},
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.OK,
                    summary="Health lifetime cannot be obtained",
                ),
            ],
            id="If the health lifetime values is below 0, the result of the second check result is OK with an explanation that the health lifetime cannot be obtained.",
        ),
        pytest.param(
            "1996492800",
            {"health_lifetime_perc": (20.0, 15.0)},
            {"1996492800": PCIeFlashModule("1996492800", "1", 0.00)},
            [
                Result(state=State.OK, summary="Status: normal"),
                Result(
                    state=State.CRIT,
                    summary="Health lifetime: 0% (warn/crit below 20.00%/15.00%)",
                ),
            ],
            id="If the health lifetime values is 0, the check will compare the value to the WARN/CRIT levels and return an appropriate second check result with a description of the thresholds.",
        ),
    ],
)
def test_check_fjdarye_pcie_flash_modules(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: PCIeFlashModuleSection,
    check_result: Sequence[Result | Metric],
) -> None:
    assert list(check_fjdarye_pcie_flash_modules(item, params, section)) == check_result
