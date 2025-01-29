#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, IgnoreResultsError, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import sap_hana_db_status as shds


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
def test_parse_sap_hana_db_status(info: StringTable, expected_result: Mapping[str, str]) -> None:
    assert shds.parse_sap_hana_db_status(info) == expected_result


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
    info: StringTable, expected_result: Sequence[Service]
) -> None:
    assert (
        list(shds.discover_sap_hana_db_status(shds.parse_sap_hana_db_status(info), None))
        == expected_result
    )


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
    item: str, info: StringTable, expected_result: CheckResult
) -> None:
    section = shds.parse_sap_hana_db_status(info)
    assert list(shds.check_sap_hana_db_status(item, section, None)) == expected_result


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
def test_check_sap_hana_db_status_stale(item: str, info: StringTable) -> None:
    section = shds.parse_sap_hana_db_status(info)
    with pytest.raises(IgnoreResultsError):
        list(shds.check_sap_hana_db_status(item, section, None))


def test_check_sap_hana_ddb_status_passive_ok() -> None:
    section = shds.parse_sap_hana_db_status(
        [
            ["[[HXE 98]]"],
            [
                "Status: error, Details: hdbsql ERROR: * -10709: Connection failed (RTE:[89006] System call 'connect' failed, rc=113:No route to host"
            ],
        ]
    )
    assert all(
        r.state is State.OK
        for r in shds.check_sap_hana_db_status(
            "HXE 98", section, {"HXE 98": {"sys_repl_status": "12"}}
        )
        if isinstance(r, Result)
    )
