#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import SectionName

from cmk.checkers.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            {"HXE 98": "OK"},
        )
    ],
)
def test_parse_sap_hana_db_status(
    fix_register: FixRegister, info: StringTable, expected_result: Mapping[str, str]
) -> None:
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_db_status")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            [Service(item="HXE 98")],
        ),
    ],
)
def test_inventory_sap_hana_db_status(
    fix_register: FixRegister, info: StringTable, expected_result: Sequence[Service]
) -> None:
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        pytest.param(
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            [Result(state=State.OK, summary="OK")],
            id="db status OK",
        ),
        pytest.param(
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["WARNING"],
            ],
            [Result(state=State.WARN, summary="WARNING")],
            id="db status WARNING",
        ),
        pytest.param(
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["DB status failed: * -10104: Invalid value for KEY"],
            ],
            [Result(state=State.CRIT, summary="DB status failed: * -10104: Invalid value for KEY")],
            id="db status error",
        ),
    ],
)
def test_check_sap_hana_db_status(
    fix_register: FixRegister, item: str, info: StringTable, expected_result: CheckResult
) -> None:
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    assert list(plugin.check_function(item, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_db_status_stale(
    fix_register: FixRegister, item: str, info: StringTable
) -> None:
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    with pytest.raises(IgnoreResultsError):
        list(plugin.check_function(item, section))
