#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.seh.agent_based.seh_ports import (
    check_seh_ports,
    discover_seh_ports,
    parse_seh_ports,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    ["2.0", "20848_Ent_GNSMART2", "010.099.005.209", "15"],
                    ["3.0", "20673_GNSMART1_Daten", "010.028.103.077", "4"],
                    ["4.0", "20557_Ent_SSR-Post", "010.028.103.076", "5"],
                    ["5.0", "20676_Postprocessing", "010.028.103.075", "6"],
                    ["6.0", "20675_Postprocessing", "SAPOS-Admin (010.099.005.208)", "7"],
                    ["7.0", "20785_Ent_GNSMART2", "010.099.005.111", "8"],
                    ["8.0", "20786_Ent_GNSMART2", "010.099.005.202", "12"],
                    ["9.0", "20737_GNSMART1_Vernetzung_NI", "010.028.103.078", "10"],
                    ["10.0", "20119_Postprocessing", "ent.westphal (010.028.130.016)", "20"],
                    ["12.0", "20672_GNSMART1_Vernetzung_NI", "SAPOS-Admin (010.099.005.205)", "3"],
                    ["13.0", "20674_GNSMART1_alles", "010.099.005.102", "14"],
                    ["14.0", "20414_SSR-Post", "010.099.005.112", "19"],
                    ["15.0", "20833_GNSMART1_Vernetzung_DE", "010.099.005.207", "16"],
                    ["16.0", "20606_GNSMART1_PE-Client", "SAPOS-Admin (010.099.005.204)", "17"],
                    ["17.0", "20387_GNSMART1_Daten", "SAPOS-Admin (010.099.005.206)", "18"],
                    ["18.0", "20600_GNSMART1_RxTools", "-", "0"],
                    ["19.0", "20837_Ent_GNSMART2", "Available", "2"],
                    ["20.0", "Test", "SAPOS-Admin (010.099.005.203)", "9"],
                    ["21.0", "", "010.099.005.114", "13"],
                ]
            ],
            [
                Service(item="10", parameters={"status_at_discovery": "010.028.103.078"}),
                Service(item="12", parameters={"status_at_discovery": "010.099.005.202"}),
                Service(item="13", parameters={"status_at_discovery": "010.099.005.114"}),
                Service(item="14", parameters={"status_at_discovery": "010.099.005.102"}),
                Service(item="15", parameters={"status_at_discovery": "010.099.005.209"}),
                Service(item="16", parameters={"status_at_discovery": "010.099.005.207"}),
                Service(
                    item="17", parameters={"status_at_discovery": "SAPOS-Admin (010.099.005.204)"}
                ),
                Service(
                    item="18", parameters={"status_at_discovery": "SAPOS-Admin (010.099.005.206)"}
                ),
                Service(item="19", parameters={"status_at_discovery": "010.099.005.112"}),
                Service(item="2", parameters={"status_at_discovery": "Available"}),
                Service(
                    item="20", parameters={"status_at_discovery": "ent.westphal (010.028.130.016)"}
                ),
                Service(
                    item="3", parameters={"status_at_discovery": "SAPOS-Admin (010.099.005.205)"}
                ),
                Service(item="4", parameters={"status_at_discovery": "010.028.103.077"}),
                Service(item="5", parameters={"status_at_discovery": "010.028.103.076"}),
                Service(item="6", parameters={"status_at_discovery": "010.028.103.075"}),
                Service(
                    item="7", parameters={"status_at_discovery": "SAPOS-Admin (010.099.005.208)"}
                ),
                Service(item="8", parameters={"status_at_discovery": "010.099.005.111"}),
                Service(
                    item="9", parameters={"status_at_discovery": "SAPOS-Admin (010.099.005.203)"}
                ),
            ],
        ),
    ],
)
def test_discover_seh_ports(
    string_table: list[StringTable],
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for seh_ports check."""
    parsed = parse_seh_ports(string_table)
    result = list(discover_seh_ports(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "8",
            {"status_at_discovery": "010.099.005.111"},
            [
                [
                    ["2.0", "20848_Ent_GNSMART2", "010.099.005.209", "15"],
                    ["3.0", "20673_GNSMART1_Daten", "010.028.103.077", "4"],
                    ["4.0", "20557_Ent_SSR-Post", "010.028.103.076", "5"],
                    ["5.0", "20676_Postprocessing", "010.028.103.075", "6"],
                    ["6.0", "20675_Postprocessing", "SAPOS-Admin (010.099.005.208)", "7"],
                    ["7.0", "20785_Ent_GNSMART2", "010.099.005.111", "8"],
                    ["8.0", "20786_Ent_GNSMART2", "010.099.005.202", "12"],
                    ["9.0", "20737_GNSMART1_Vernetzung_NI", "010.028.103.078", "10"],
                    ["10.0", "20119_Postprocessing", "ent.westphal (010.028.130.016)", "20"],
                    ["12.0", "20672_GNSMART1_Vernetzung_NI", "SAPOS-Admin (010.099.005.205)", "3"],
                    ["13.0", "20674_GNSMART1_alles", "010.099.005.102", "14"],
                    ["14.0", "20414_SSR-Post", "010.099.005.112", "19"],
                    ["15.0", "20833_GNSMART1_Vernetzung_DE", "010.099.005.207", "16"],
                    ["16.0", "20606_GNSMART1_PE-Client", "SAPOS-Admin (010.099.005.204)", "17"],
                    ["17.0", "20387_GNSMART1_Daten", "SAPOS-Admin (010.099.005.206)", "18"],
                    ["18.0", "20600_GNSMART1_RxTools", "-", "0"],
                    ["19.0", "20837_Ent_GNSMART2", "Available", "2"],
                    ["20.0", "Test", "SAPOS-Admin (010.099.005.203)", "9"],
                    ["21.0", "", "010.099.005.114", "13"],
                ]
            ],
            [
                Result(state=State.OK, summary="Tag: 20786_Ent_GNSMART2"),
                Result(state=State.OK, summary="Status: 010.099.005.111"),
            ],
        ),
        (
            "9",
            {"status_at_discovery": "Available"},
            [
                [
                    ["2.0", "20848_Ent_GNSMART2", "010.099.005.209", "15"],
                    ["3.0", "20673_GNSMART1_Daten", "010.028.103.077", "4"],
                    ["4.0", "20557_Ent_SSR-Post", "010.028.103.076", "5"],
                    ["5.0", "20676_Postprocessing", "010.028.103.075", "6"],
                    ["6.0", "20675_Postprocessing", "SAPOS-Admin (010.099.005.208)", "7"],
                    ["7.0", "20785_Ent_GNSMART2", "010.099.005.111", "8"],
                    ["8.0", "20786_Ent_GNSMART2", "010.099.005.202", "12"],
                    ["9.0", "20737_GNSMART1_Vernetzung_NI", "010.028.103.078", "10"],
                    ["10.0", "20119_Postprocessing", "ent.westphal (010.028.130.016)", "20"],
                    ["12.0", "20672_GNSMART1_Vernetzung_NI", "SAPOS-Admin (010.099.005.205)", "3"],
                    ["13.0", "20674_GNSMART1_alles", "010.099.005.102", "14"],
                    ["14.0", "20414_SSR-Post", "010.099.005.112", "19"],
                    ["15.0", "20833_GNSMART1_Vernetzung_DE", "010.099.005.207", "16"],
                    ["16.0", "20606_GNSMART1_PE-Client", "SAPOS-Admin (010.099.005.204)", "17"],
                    ["17.0", "20387_GNSMART1_Daten", "SAPOS-Admin (010.099.005.206)", "18"],
                    ["18.0", "20600_GNSMART1_RxTools", "-", "0"],
                    ["19.0", "20837_Ent_GNSMART2", "Available", "2"],
                    ["20.0", "Test", "SAPOS-Admin (010.099.005.203)", "9"],
                    ["21.0", "", "010.099.005.114", "13"],
                ]
            ],
            [
                Result(state=State.OK, summary="Tag: 20737_GNSMART1_Vernetzung_NI"),
                Result(state=State.OK, summary="Status: SAPOS-Admin (010.099.005.203)"),
                Result(state=State.WARN, summary="Status during discovery: Available"),
            ],
        ),
        (
            "9",
            {"status_at_discovery": None},
            [
                [
                    ["2.0", "20848_Ent_GNSMART2", "010.099.005.209", "15"],
                    ["3.0", "20673_GNSMART1_Daten", "010.028.103.077", "4"],
                    ["4.0", "20557_Ent_SSR-Post", "010.028.103.076", "5"],
                    ["5.0", "20676_Postprocessing", "010.028.103.075", "6"],
                    ["6.0", "20675_Postprocessing", "SAPOS-Admin (010.099.005.208)", "7"],
                    ["7.0", "20785_Ent_GNSMART2", "010.099.005.111", "8"],
                    ["8.0", "20786_Ent_GNSMART2", "010.099.005.202", "12"],
                    ["9.0", "20737_GNSMART1_Vernetzung_NI", "010.028.103.078", "10"],
                    ["10.0", "20119_Postprocessing", "ent.westphal (010.028.130.016)", "20"],
                    ["12.0", "20672_GNSMART1_Vernetzung_NI", "SAPOS-Admin (010.099.005.205)", "3"],
                    ["13.0", "20674_GNSMART1_alles", "010.099.005.102", "14"],
                    ["14.0", "20414_SSR-Post", "010.099.005.112", "19"],
                    ["15.0", "20833_GNSMART1_Vernetzung_DE", "010.099.005.207", "16"],
                    ["16.0", "20606_GNSMART1_PE-Client", "SAPOS-Admin (010.099.005.204)", "17"],
                    ["17.0", "20387_GNSMART1_Daten", "SAPOS-Admin (010.099.005.206)", "18"],
                    ["18.0", "20600_GNSMART1_RxTools", "-", "0"],
                    ["19.0", "20837_Ent_GNSMART2", "Available", "2"],
                    ["20.0", "Test", "SAPOS-Admin (010.099.005.203)", "9"],
                    ["21.0", "", "010.099.005.114", "13"],
                ]
            ],
            [
                Result(state=State.OK, summary="Tag: 20737_GNSMART1_Vernetzung_NI"),
                Result(state=State.OK, summary="Status: SAPOS-Admin (010.099.005.203)"),
                Result(state=State.WARN, summary="Status during discovery: unknown"),
            ],
        ),
    ],
)
def test_check_seh_ports(
    item: str,
    params: Mapping[str, object],
    string_table: list[StringTable],
    expected_results: Sequence[Result],
) -> None:
    """Test check function for seh_ports check."""
    parsed = parse_seh_ports(string_table)
    result = list(check_seh_ports(item, params, parsed))
    assert result == expected_results
