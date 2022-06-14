#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.mssql_mirroring import (
    check_mssql_mirroring,
    cluster_check_mssql_mirroring,
    discover_mssql_mirroring,
    MirroringConfig,
    parse_mssql_mirroring,
)


@pytest.mark.parametrize(
    "string_table, parsed_config",
    [
        (
            [
                ["MBEAN"],
                [
                    "server-france\\MBEAN",
                    "TRAVELER",
                    "4",
                    "SYNCHRONIZED",
                    "1",
                    "PRINCIPAL",
                    "2",
                    "FULL",
                    "TCP://server-guatemala.net:22",
                    "server-guatemala\\MDOT",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                [
                    "server-france\\MBEAN",
                    "FARMER",
                    "4",
                    "SYNCHRONIZED",
                    "1",
                    "PRINCIPAL",
                    "2",
                    "FULL",
                    "TCP://server-guatemala.net:22",
                    "server-guatemala\\MDOT",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                ["MDOT"],
                [
                    "server-guatemala\\MDOT",
                    "TRAVELER",
                    "4",
                    "SYNCHRONIZED",
                    "2",
                    "MIRROR",
                    "2",
                    "FULL",
                    "TCP://server-france.net:22",
                    "server-france\\MBEAN",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                [
                    "server-guatemala\\MDOT",
                    "FARMER",
                    "4",
                    "SYNCHRONIZED",
                    "2",
                    "MIRROR",
                    "2",
                    "FULL",
                    "TCP://server-france.net:22",
                    "server-france\\MBEAN",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
            ],
            {
                "TRAVELER": MirroringConfig(
                    server_name="server-france\\MBEAN",
                    database_name="TRAVELER",
                    mirroring_state=4,
                    mirroring_state_desc="SYNCHRONIZED",
                    mirroring_role=1,
                    mirroring_role_desc="PRINCIPAL",
                    mirroring_safety_level=2,
                    mirroring_safety_level_desc="FULL",
                    mirroring_partner_name="TCP://server-guatemala.net:22",
                    mirroring_partner_instance="server-guatemala\\MDOT",
                    mirroring_witness_name="TCP://server-vientam.net:22",
                    mirroring_witness_state=1,
                    mirroring_witness_state_desc="CONNECTED",
                ),
                "FARMER": MirroringConfig(
                    server_name="server-france\\MBEAN",
                    database_name="FARMER",
                    mirroring_state=4,
                    mirroring_state_desc="SYNCHRONIZED",
                    mirroring_role=1,
                    mirroring_role_desc="PRINCIPAL",
                    mirroring_safety_level=2,
                    mirroring_safety_level_desc="FULL",
                    mirroring_partner_name="TCP://server-guatemala.net:22",
                    mirroring_partner_instance="server-guatemala\\MDOT",
                    mirroring_witness_name="TCP://server-vientam.net:22",
                    mirroring_witness_state=1,
                    mirroring_witness_state_desc="CONNECTED",
                ),
            },
        ),
    ],
)
def test_parse_mssql_mirroring(string_table, parsed_config) -> None:
    assert parse_mssql_mirroring(string_table) == parsed_config


@pytest.mark.parametrize(
    "string_table, discovered_services",
    [
        (
            [
                ["MBEAN"],
                [
                    "server-france\\MBEAN",
                    "TRAVELER",
                    "4",
                    "SYNCHRONIZED",
                    "1",
                    "PRINCIPAL",
                    "2",
                    "FULL",
                    "TCP://server-guatemala.net:22",
                    "server-guatemala\\MDOT",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                [
                    "server-france\\MBEAN",
                    "FARMER",
                    "4",
                    "SYNCHRONIZED",
                    "1",
                    "PRINCIPAL",
                    "2",
                    "FULL",
                    "TCP://server-guatemala.net:22",
                    "server-guatemala\\MDOT",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                ["MDOT"],
                [
                    "server-guatemala\\MDOT",
                    "TRAVELER",
                    "4",
                    "SYNCHRONIZED",
                    "2",
                    "MIRROR",
                    "2",
                    "FULL",
                    "TCP://server-france.net:22",
                    "server-france\\MBEAN",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
                [
                    "server-guatemala\\MDOT",
                    "FARMER",
                    "4",
                    "SYNCHRONIZED",
                    "2",
                    "MIRROR",
                    "2",
                    "FULL",
                    "TCP://server-france.net:22",
                    "server-france\\MBEAN",
                    "TCP://server-vientam.net:22",
                    "1",
                    "CONNECTED",
                ],
            ],
            [
                Service(item="TRAVELER"),
                Service(item="FARMER"),
            ],
        ),
    ],
)
def test_discover_mssql_mirroring(string_table, discovered_services) -> None:
    assert (
        list(discover_mssql_mirroring(parse_mssql_mirroring(string_table))) == discovered_services
    )


@pytest.mark.parametrize(
    "item, params, section, check_result",
    [
        (
            "TRAVELER",
            {
                "mirroring_state_criticality": 0,
                "mirroring_witness_state_criticality": 0,
            },
            {
                "TRAVELER": MirroringConfig(
                    server_name="server-france\\MBEAN",
                    database_name="TRAVELER",
                    mirroring_state=4,
                    mirroring_state_desc="SYNCHRONIZED",
                    mirroring_role=1,
                    mirroring_role_desc="PRINCIPAL",
                    mirroring_safety_level=2,
                    mirroring_safety_level_desc="FULL",
                    mirroring_partner_name="TCP://server-guatemala.net:22",
                    mirroring_partner_instance="server-guatemala\\MDOT",
                    mirroring_witness_name="TCP://server-vientam.net:22",
                    mirroring_witness_state=1,
                    mirroring_witness_state_desc="CONNECTED",
                ),
            },
            [
                Result(state=State.OK, summary="Principal: server-france\\MBEAN"),
                Result(state=State.OK, summary="Mirror: server-guatemala\\MDOT"),
                Result(state=State.OK, notice="Mirroring state: SYNCHRONIZED"),
                Result(state=State.OK, notice="Mirroring witness state: CONNECTED"),
                Result(state=State.OK, notice="Mirroring safety level: FULL"),
                Result(
                    state=State.OK, notice="Mirroring partner name: TCP://server-guatemala.net:22"
                ),
                Result(
                    state=State.OK, notice="Mirroring witness name: TCP://server-vientam.net:22"
                ),
            ],
        ),
        (
            "FARMER",
            {
                "mirroring_state_criticality": 2,
                "mirroring_witness_state_criticality": 2,
            },
            {
                "FARMER": MirroringConfig(
                    server_name="server-france\\MBEAN",
                    database_name="FARMER",
                    mirroring_state=1,
                    mirroring_state_desc="DISCONNECTED",
                    mirroring_role=1,
                    mirroring_role_desc="PRINCIPAL",
                    mirroring_safety_level=2,
                    mirroring_safety_level_desc="FULL",
                    mirroring_partner_name="TCP://server-guatemala.net:22",
                    mirroring_partner_instance="server-guatemala\\MDOT",
                    mirroring_witness_name="TCP://server-vientam.net:22",
                    mirroring_witness_state=2,
                    mirroring_witness_state_desc="DISCONNECTED",
                ),
            },
            [
                Result(state=State.OK, summary="Principal: server-france\\MBEAN"),
                Result(state=State.OK, summary="Mirror: server-guatemala\\MDOT"),
                Result(state=State.CRIT, notice="Mirroring state: DISCONNECTED"),
                Result(state=State.CRIT, notice="Mirroring witness state: DISCONNECTED"),
                Result(state=State.OK, notice="Mirroring safety level: FULL"),
                Result(
                    state=State.OK, notice="Mirroring partner name: TCP://server-guatemala.net:22"
                ),
                Result(
                    state=State.OK, notice="Mirroring witness name: TCP://server-vientam.net:22"
                ),
            ],
        ),
    ],
)
def test_check_mssql_mirroring(item, params, section, check_result) -> None:
    assert list(check_mssql_mirroring(item, params, section)) == check_result


@pytest.mark.parametrize(
    "item, params, section, check_result",
    [
        (
            "TRAVELER",
            {
                "mirroring_state_criticality": 0,
                "mirroring_witness_state_criticality": 0,
            },
            {
                "node0": {
                    "TRAVELER": MirroringConfig(
                        server_name="server-france\\MBEAN",
                        database_name="TRAVELER",
                        mirroring_state=4,
                        mirroring_state_desc="SYNCHRONIZED",
                        mirroring_role=1,
                        mirroring_role_desc="PRINCIPAL",
                        mirroring_safety_level=2,
                        mirroring_safety_level_desc="FULL",
                        mirroring_partner_name="TCP://server-guatemala.net:22",
                        mirroring_partner_instance="server-guatemala\\MDOT",
                        mirroring_witness_name="TCP://server-vientam.net:22",
                        mirroring_witness_state=1,
                        mirroring_witness_state_desc="CONNECTED",
                    ),
                },
                "node1": {
                    "FARMER": MirroringConfig(
                        server_name="server-france\\MBEAN",
                        database_name="FARMER",
                        mirroring_state=1,
                        mirroring_state_desc="DISCONNECTED",
                        mirroring_role=1,
                        mirroring_role_desc="PRINCIPAL",
                        mirroring_safety_level=2,
                        mirroring_safety_level_desc="FULL",
                        mirroring_partner_name="TCP://server-guatemala.net:22",
                        mirroring_partner_instance="server-guatemala\\MDOT",
                        mirroring_witness_name="TCP://server-vientam.net:22",
                        mirroring_witness_state=2,
                        mirroring_witness_state_desc="DISCONNECTED",
                    ),
                },
            },
            [
                Result(state=State.OK, summary="Principal: server-france\\MBEAN"),
                Result(state=State.OK, summary="Mirror: server-guatemala\\MDOT"),
                Result(state=State.OK, notice="Mirroring state: SYNCHRONIZED"),
                Result(state=State.OK, notice="Mirroring witness state: CONNECTED"),
                Result(state=State.OK, notice="Mirroring safety level: FULL"),
                Result(
                    state=State.OK, notice="Mirroring partner name: TCP://server-guatemala.net:22"
                ),
                Result(
                    state=State.OK, notice="Mirroring witness name: TCP://server-vientam.net:22"
                ),
            ],
        ),
        (
            "TRAVELER",
            {
                "mirroring_state_criticality": 0,
                "mirroring_witness_state_criticality": 0,
            },
            {
                "node0": {
                    "TRAVELER": MirroringConfig(
                        server_name="server-france\\MBEAN",
                        database_name="TRAVELER",
                        mirroring_state=4,
                        mirroring_state_desc="SYNCHRONIZED",
                        mirroring_role=1,
                        mirroring_role_desc="PRINCIPAL",
                        mirroring_safety_level=2,
                        mirroring_safety_level_desc="FULL",
                        mirroring_partner_name="TCP://server-guatemala.net:22",
                        mirroring_partner_instance="server-guatemala\\MDOT",
                        mirroring_witness_name="TCP://server-vientam.net:22",
                        mirroring_witness_state=1,
                        mirroring_witness_state_desc="CONNECTED",
                    ),
                },
                "node1": {
                    "TRAVELER": MirroringConfig(
                        server_name="server-france\\MBEAN",
                        database_name="TRAVELER",
                        mirroring_state=4,
                        mirroring_state_desc="SYNCHRONIZED",
                        mirroring_role=1,
                        mirroring_role_desc="PRINCIPAL",
                        mirroring_safety_level=2,
                        mirroring_safety_level_desc="FULL",
                        mirroring_partner_name="TCP://server-guatemala.net:22",
                        mirroring_partner_instance="server-guatemala\\MDOT",
                        mirroring_witness_name="TCP://server-vientam.net:22",
                        mirroring_witness_state=1,
                        mirroring_witness_state_desc="CONNECTED",
                    ),
                },
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Found principal database on more than one node: node0, node1",
                ),
            ],
        ),
        (
            "TRAVELER",
            {
                "mirroring_state_criticality": 0,
                "mirroring_witness_state_criticality": 0,
            },
            {
                "node0": {},
                "node1": {},
            },
            [],
        ),
    ],
)
def test_cluster_check_mssql_mirroring(item, params, section, check_result) -> None:
    assert list(cluster_check_mssql_mirroring(item, params, section)) == check_result
