#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v1 import Result, State
from cmk.plugins.hp_msa.agent_based.health import check_hp_msa_health
from cmk.plugins.hp_msa.agent_based.hp_msa_system import parse_hp_msa_system


@pytest.mark.parametrize(
    "item, string_table, expected",
    [
        pytest.param(
            "hostport_A1",
            [
                ["port", "3", "durable-id", "hostport_A1"],
                ["system", "1", "system-name", "hostport_A1"],
                ["port", "3", "controller", "A"],
                ["port", "3", "controller-numeric", "1"],
                ["port", "3", "port", "A1"],
                ["port", "3", "port-type", "FC"],
                ["port", "3", "status", "Aktiv"],
                ["port", "3", "status-numeric", "0"],
                ["port", "3", "health", "OK"],
                ["port", "3", "health-numeric", "0"],
                ["port", "3", "health-reason", ""],
            ],
            [
                Result(
                    state=State.OK,
                    summary="Status: OK",
                )
            ],
        ),
        pytest.param(
            "hostport_A2",
            [
                ["port", "3", "durable-id", "hostport_A2"],
                ["system", "1", "system-name", "hostport_A2"],
                ["port", "3", "controller", "A"],
                ["port", "3", "controller-numeric", "2"],
                ["port", "3", "port", "A2"],
                ["port", "3", "port-type", "FC"],
                ["port", "3", "status", "Aktiv"],
                ["port", "3", "status-numeric", "0"],
                ["port", "3", "health", "Nicht Gut"],
                ["port", "3", "health-numeric", "4"],
                ["port", "3", "health-reason", "fallback error"],
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Status: not present (fallback error)",
                )
            ],
        ),
        pytest.param(
            "Uninitialized Name",
            [
                ["system", "1", "system-name", "Uninitialized", "Name"],
                ["system", "1", "health", "Unbekannt"],
                ["system", "1", "health-numeric", "3"],
                [
                    "system",
                    "1",
                    "health-reason",
                    "Der",
                    "Partner-MC",
                    "ist",
                    "entweder",
                    "nicht",
                    "erreichbar,",
                    "kommuniziert",
                    "nicht",
                    "oder",
                    "ist",
                    "nicht",
                    "mit",
                    "dem",
                    "lokalen",
                    "MC",
                    "synchronisiert.",
                    "Der",
                    "Systemzustand",
                    "kann",
                    "von",
                    "diesem",
                    "Controller",
                    "nicht",
                    "berechnet",
                    "werden.",
                ],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Status: unknown (Der Partner-MC ist entweder nicht erreichbar, kommuniziert nicht oder ist nicht mit dem lokalen MC synchronisiert. Der Systemzustand kann von diesem Controller nicht berechnet werden.)",
                )
            ],
        ),
    ],
)
def test_check_hp_msa_health(
    item: str,
    string_table: list[list[str]],
    expected: list[Result],
) -> None:
    assert expected == list(check_hp_msa_health(item, parse_hp_msa_system(string_table)))
