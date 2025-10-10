#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import (
    CheckResult,
    get_value_store,
    Metric,
    Result,
    State,
)
from cmk.plugins.netapp.agent_based.netapp_ontap_cpu import (
    check_netapp_ontap_cpu_utilization,
    check_netapp_ontap_nvram_bat,
)
from cmk.plugins.netapp.models import NodeModel


class NodeModelFactory(ModelFactory):
    __model__ = NodeModel


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "node_model, params, expected_state",
    [
        pytest.param(
            NodeModelFactory.build(
                name="cpu1",
                processor_utilization=30,
                processor_utilization_timestamp="2025-09-30T15:00:00Z",
                cpu_count=2,
                version={"generation": 8, "major": 15, "minor": 1},
            ),
            {"levels": (90.0, 95.0)},
            State.OK,
            id="cpu utilization status ok",
        ),
        pytest.param(
            NodeModelFactory.build(
                name="cpu1",
                processor_utilization=30,
                processor_utilization_timestamp="2025-09-30T15:00:00Z",
                cpu_count=2,
                version={"generation": 8, "major": 15, "minor": 1},
            ),
            {"levels": (30.0, 95.0)},
            State.WARN,
            id="cpu utilization status warn",
        ),
    ],
)
def test_check_netapp_ontap_cpu_utilization(
    node_model: NodeModel,
    params: Mapping[str, Any],
    expected_state: State,
) -> None:
    section = {node_model.name: node_model}

    result = list(check_netapp_ontap_cpu_utilization(item="cpu1", params=params, section=section))

    assert isinstance(result[0], Result)
    assert result[0].state == expected_state and result[0].summary.startswith("Total CPU: 30.00%")
    assert isinstance(result[1], Metric)
    assert result[1].name == "util"
    assert result[2] == Result(state=State.OK, summary="Number of CPUs: 2 CPUs")


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "node_model, params, expected_state",
    [
        pytest.param(
            NodeModelFactory.build(
                name="cpu1",
                processor_utilization=30,
                processor_utilization_timestamp="2025-09-30T15:00:00Z",
                cpu_count=2,
                version={"generation": 8, "major": 15, "minor": 1},
            ),
            {"levels": (90.0, 95.0), "average": 10},
            State.OK,
            id="cpu utilization status ok",
        ),
    ],
)
def test_check_netapp_ontap_cpu_utilization_average(
    node_model: NodeModel,
    params: Mapping[str, Any],
    expected_state: State,
) -> None:
    get_value_store().update(
        {"cpu_utilization.avg": (1759243800.0, 1759243800.0, 60)}
    )  # 2025-09-30T14:50:00Z
    section = {node_model.name: node_model}

    result = list(check_netapp_ontap_cpu_utilization(item="cpu1", params=params, section=section))

    assert isinstance(result[1], Result)
    assert result[1].state == expected_state and result[1].summary.startswith(
        "Total CPU (10 min average): 45.00%"
    )
    assert isinstance(result[2], Metric)
    assert result[2].name == "util_average"
    assert result[2] == Metric("util_average", 45.0, levels=(90.0, 95.0), boundaries=(0.0, None))


@pytest.mark.usefixtures("initialised_item_state")
def test_check_netapp_ontap_cpu_utilization_not_present() -> None:
    get_value_store().update({"netapp_cpu_util": (60, 15)})

    node_model = NodeModelFactory.build(name="cpu1")
    section = {node_model.name: node_model}

    result = check_netapp_ontap_cpu_utilization(item="cpu_not_present", params={}, section=section)
    assert len(list(result)) == 0


@pytest.mark.parametrize(
    "node_model, expected_results",
    [
        pytest.param(
            NodeModelFactory.build(name="cpu1", battery_state="battery_ok"),
            [Result(state=State.OK, summary="Status: Battery Ok")],
            id="nvram battery status ok",
        ),
        pytest.param(
            NodeModelFactory.build(name="cpu1", battery_state="status_not_mapped"),
            [Result(state=State.UNKNOWN, summary="Status: Status Not Mapped")],
            id="nvram battery status unknown",
        ),
    ],
)
def test_check_netapp_ontap_nvram_bat_ok(
    node_model: NodeModel,
    expected_results: CheckResult,
) -> None:
    section = {node_model.name: node_model}

    result = check_netapp_ontap_nvram_bat(item="cpu1", section=section)
    assert list(result) == expected_results
