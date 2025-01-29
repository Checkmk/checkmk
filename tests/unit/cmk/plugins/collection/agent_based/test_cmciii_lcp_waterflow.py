#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.cmciii_lcp_waterflow import (
    check_cmciii_lcp_waterflow,
    inventory_cmciii_lcp_waterflow,
    parse_cmciii_lcp_waterflow,
    Section,
)


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                [
                    "LCP_B5_Waterflow",
                    "0.0 l/min",
                    "130.0 l/min",
                    "0.0 l/min",
                    "OK",
                    "2",
                    "Control-Valve",
                    "32 %",
                    "OK",
                    "2",
                    "Cooling-Capacity",
                    "0 W",
                    "OK",
                ],
            ],
            Section(
                name="LCP_B5_Waterflow",
                flow=0.0,
                unit="l/min",
                maxflow=130.0,
                minflow=0.0,
                status="OK",
            ),
            id="Waterflow measurements are parsed correctly",
        ),
    ],
)
def test_parse_cmciii_lcp_waterflow(string_table: StringTable, section: Section) -> None:
    assert parse_cmciii_lcp_waterflow(string_table) == section


def test_parse_cmciii_lcp_waterflow_empty_section() -> None:
    assert parse_cmciii_lcp_waterflow([]) is None


@pytest.mark.parametrize(
    "section, discovered_items",
    [
        pytest.param(
            Section(
                name="Waterflow", flow=0.0, unit="l/min", maxflow=130.0, minflow=0.0, status="OK"
            ),
            [Service()],
            id="Waterflow sensor is discovered within OID range.",
        ),
    ],
)
def test_discover_cmciii_lcp_waterflow(
    section: Section, discovered_items: Sequence[Service]
) -> None:
    assert list(inventory_cmciii_lcp_waterflow(section)) == discovered_items


@pytest.mark.parametrize(
    "section, check_results",
    [
        pytest.param(
            Section(
                name="Waterflow", flow=0.0, unit="l/min", maxflow=130.0, minflow=0.0, status="OK"
            ),
            [
                Result(state=State.OK, summary="Waterflow Status: OK"),
                Result(state=State.OK, summary="Flow: 0.0"),
                Result(state=State.OK, summary="MinFlow: 0.0"),
                Result(state=State.OK, summary="MaxFlow: 130.0"),
                Metric("flow", 0.0, levels=(130.0, 1e309)),
            ],
            id="Check results of waterflow sensor measurements",
        ),
    ],
)
def test_check_cmciii_lcp_waterflow(section: Section, check_results: Sequence) -> None:
    assert list(check_cmciii_lcp_waterflow(section)) == check_results
