#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.netapp.agent_based.netapp_ontap_fcp as ontap_fcp
from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_fcp import (
    _io_bytes_results,
    _io_ops_results,
    _latency_results,
    _speed_result,
    check_netapp_ontap_fcp,
)
from cmk.plugins.netapp.models import FcInterfaceTrafficCountersModel, FcPortModel

NOW_SIMULATED = "1988-06-08 17:00:00.000000"
NOW_SIMULATED_SECONDS = (
    datetime.strptime(NOW_SIMULATED, "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()
LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    # According to NetApp's "Performance Management Design Guide",
    # the latency is a function of `total_ops`.
    value_store_patched = {
        #                              toal_ops, last latency RATE value
        "test_latency.avg_read_latency": (1000, 100),
        "test_latency.avg_write_latency": (1000, 100),
        #                 last time, last iops RATE value
        "test_ops.read_ops": (LAST_TIME_EPOCH, 1000),
        "test_ops.write_ops": (LAST_TIME_EPOCH, 1000),
        #                 last time, last iops RATE value
        "test_io_bytes.read_bytes": (LAST_TIME_EPOCH, 1000),
        "test_io_bytes.write_bytes": (LAST_TIME_EPOCH, 1000),
        #
        "node_name.11a.avg_read_latency": (1000, 100),
        "node_name.11a.avg_write_latency": (1000, 100),
        #                 last time, last iops RATE value
        "node_name.11a.read_ops": (LAST_TIME_EPOCH, 1000),
        "node_name.11a.write_ops": (LAST_TIME_EPOCH, 1000),
        #                 last time, last iops RATE value
        "node_name.11a.read_bytes": (LAST_TIME_EPOCH, 1000),
        "node_name.11a.write_bytes": (LAST_TIME_EPOCH, 1000),
        #
        "node_name.11b.avg_read_latency": (1000, 100),
        "node_name.11b.avg_write_latency": (1000, 100),
        #                 last time, last iops RATE value
        "node_name.11b.read_ops": (LAST_TIME_EPOCH, 1000),
        "node_name.11b.write_ops": (LAST_TIME_EPOCH, 1000),
        #                 last time, last iops RATE value
        "node_name.11b.read_bytes": (LAST_TIME_EPOCH, 1000),
        "node_name.11b.write_bytes": (LAST_TIME_EPOCH, 1000),
    }
    monkeypatch.setattr(ontap_fcp, "get_value_store", lambda: value_store_patched)


class FcInterfaceTrafficCountersModelFactory(ModelFactory):
    __model__ = FcInterfaceTrafficCountersModel


class FcPortModelFactory(ModelFactory):
    __model__ = FcPortModel


def test_latency_results_ok(value_store_patch: None) -> None:
    fcp_if_counters = {
        "total_ops": 2000,
        "avg_read_latency": 300000,
        "avg_write_latency": 500000,
        "now": time.time(),
    }

    result = list(_latency_results(item="test_latency", params={}, fcp_if=fcp_if_counters))

    assert isinstance(result[0], Result)
    assert result[0].state == State.OK

    assert isinstance(result[1], Metric)
    assert result[1].name == "avg_read_latency_latency" and result[1].value == 0.2

    assert isinstance(result[3], Metric)
    assert result[3].name == "avg_write_latency_latency" and result[3].value == 0.4


def test_latency_results_warn(value_store_patch: None) -> None:
    fcp_if_counters = {
        "total_ops": 2000,
        "avg_read_latency": 300000,
        "avg_write_latency": 500000,
    }

    result = list(
        _latency_results(
            item="test_latency", params={"avg_read_latency": (0.1, 0.3)}, fcp_if=fcp_if_counters
        )
    )
    assert isinstance(result[0], Result)
    assert result[0].state == State.WARN and result[0].summary.startswith("Read Latency")

    assert isinstance(result[1], Metric)
    assert result[1].name == "avg_read_latency_latency" and result[1].value == 0.2

    assert isinstance(result[3], Metric)
    assert result[3].name == "avg_write_latency_latency" and result[3].value == 0.4


def test_io_ops_results(value_store_patch: None) -> None:
    fcp_if_counters = {
        "read_ops": 2000,
        "write_ops": 3000,
        "now": NOW_SIMULATED_SECONDS,
    }

    result = list(_io_ops_results(item="test_ops", params={}, fcp_if=fcp_if_counters))

    assert isinstance(result[0], Result)
    assert result[0].state == State.OK and result[0].details.startswith("Read OPS")

    assert isinstance(result[1], Metric)
    assert result[1].name == "read_ops"

    assert isinstance(result[2], Result)
    assert result[2].state == State.OK and result[2].details.startswith("Write OPS")

    assert isinstance(result[3], Metric)
    assert result[3].name == "write_ops"


@pytest.mark.parametrize(
    "params, speed, expected_result",
    [
        pytest.param({}, 8000, [Result(state=State.OK, summary="Speed: 8 kBit/s")], id="speed ok"),
        pytest.param(
            {"speed": 8000},
            8000,
            [Result(state=State.OK, summary="Speed: 8 kBit/s")],
            id="speed like expected",
        ),
        pytest.param({}, None, [], id="speed None, expected None"),
        pytest.param(
            {"speed": 8000},
            None,
            [Result(state=State.WARN, summary="Speed: unknown (expected: 8 kBit/s)")],
            id="speed None, expected not None",
        ),
        pytest.param(
            {"speed": 5000},
            8000,
            [Result(state=State.CRIT, summary="Speed: 8 kBit/s (expected: 5 kBit/s)")],
            id="speed not expected",
        ),
        pytest.param(
            {"inv_speed": 5000},
            8000,
            [Result(state=State.CRIT, summary="Speed: 8 kBit/s (expected: 5 kBit/s)")],
            id="speed not expected 2",
        ),
    ],
)
def test_speed_result(
    params: Mapping[str, Any], speed: int | None, expected_result: CheckResult
) -> None:
    result = list(_speed_result(params=params, speed=speed))

    assert result == expected_result


def test_io_bytes_results(value_store_patch: None) -> None:
    fcp_if_counters = {
        "read_bytes": 300000,
        "write_bytes": 200000,
        "now": NOW_SIMULATED_SECONDS,
    }

    result = list(
        _io_bytes_results(item="test_io_bytes", params={}, fcp_if=fcp_if_counters, speed=8000)
    )

    assert isinstance(result[0], Result)
    assert result[0].state == State.OK and result[0].summary.startswith("Read")
    assert isinstance(result[1], Metric)
    assert result[1].name == "read_bytes"
    assert isinstance(result[2], Result)
    assert result[2].state == State.OK and result[2].summary.startswith("Write")
    assert isinstance(result[3], Metric)
    assert result[3].name == "write_bytes"


@pytest.mark.parametrize(
    "item_name, expected_last_result",
    [
        pytest.param(
            "node_name.11a",
            Result(
                state=State.OK,
                summary="State: link_not_connected",
                details="State: link_not_connected\nAddress 50:0a:09:88:a0:a2:f2:00",
            ),
            id="port not connected",
        ),
        pytest.param(
            "node_name.11b",
            Result(
                state=State.OK,
                summary="State: online",
                details="State: online\nAddress 50:0a:09:87:a0:a2:f2:00",
            ),
            id="port connected",
        ),
    ],
)
def test_check_netapp_ontap_fcp(
    item_name: str, expected_last_result: Result, value_store_patch: None
) -> None:
    _ports_models = [
        FcPortModelFactory.build(
            name="11a",
            connected_speed=8000,
            description="Fibre Channel Target Adapter 11a (QLogic CNA 8324 (8362), rev. 2, CNA_10G)",
            enabled=True,
            node_name="node_name",
            physical_protocol="ethernet",
            state="link_not_connected",
            supported_protocols=["fcp"],
            wwnn="50:0a:09:80:80:a2:f2:00",
            wwpn="50:0a:09:88:a0:a2:f2:00",
        ),
        FcPortModelFactory.build(
            name="11b",
            connected_speed=10000,
            description="Fibre Channel Target Adapter 11b (QLogic CNA 8324 (8362), rev. 2, CNA_10G)",
            enabled=True,
            node_name="node_name",
            physical_protocol="ethernet",
            state="online",
            supported_protocols=["fcp"],
            wwnn="50:0a:09:80:80:a2:f2:00",
            wwpn="50:0a:09:87:a0:a2:f2:00",
        ),
    ]

    _interfaces_models = [
        FcInterfaceTrafficCountersModelFactory.build(
            name="interface_counter",
            counters=[
                {"name": "read_ops", "value": 2000},
                {"name": "write_ops", "value": 3000},
                {"name": "total_ops", "value": 4000},
                {"name": "read_data", "value": 300000},
                {"name": "write_data", "value": 200000},
                {"name": "average_read_latency", "value": 6000},
                {"name": "average_write_latency", "value": 7000},
            ],
            port_wwpn="50:0a:09:88:a0:a2:f2:00",
            svm_name="none",
            table="fcp_lif:port",
        ),
        FcInterfaceTrafficCountersModelFactory.build(
            name="interface_counter",
            counters=[
                {"name": "read_ops", "value": 2000},
                {"name": "write_ops", "value": 3000},
                {"name": "total_ops", "value": 4000},
                {"name": "read_data", "value": 300000},
                {"name": "write_data", "value": 200000},
                {"name": "average_read_latency", "value": 6000},
                {"name": "average_write_latency", "value": 7000},
            ],
            port_wwpn="50:0a:09:87:a0:a2:f2:00",
            svm_name="none",
            table="fcp_lif:port",
        ),
    ]
    ports_section = {f"{fc_port.node_name}.{fc_port.name}": fc_port for fc_port in _ports_models}
    interfaces_section = {
        fc_interface.port_wwpn: fc_interface for fc_interface in _interfaces_models
    }

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(
            check_netapp_ontap_fcp(
                item=item_name,
                params={},
                section_netapp_ontap_fc_ports=ports_section,
                section_netapp_ontap_fc_interfaces_counters=interfaces_section,
            )
        )

        assert len(result) == 10
        assert result[-1] == expected_last_result
