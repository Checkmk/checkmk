#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, render, Result, State, StringTable
from cmk.plugins.collection.agent_based import kube_pod_containers
from cmk.plugins.kube.schemata.api import ContainerStateType, ContainerTerminatedState
from cmk.plugins.kube.schemata.section import PodContainers

TIMESTAMP = 359
MINUTE = 60


@pytest.fixture
def num_of_containers():
    return 1


@pytest.fixture
def container_name(num_of_containers):
    return "doge" if num_of_containers == 1 else "doge-{}"


@pytest.fixture
def container_state():
    return "running"


@pytest.fixture
def timespan():
    return 0


@pytest.fixture
def start_time(timespan):
    return TIMESTAMP - timespan


@pytest.fixture
def exit_code():
    return 0


@pytest.fixture
def container_state_dict(container_state, start_time, exit_code):
    if container_state == "running":
        return {"type": "running", "start_time": start_time}
    if container_state == "waiting":
        return {"type": "waiting", "reason": "VeryReason", "detail": "so detail"}
    if container_state == "terminated":
        return {
            "type": "terminated",
            "exit_code": exit_code,
            "start_time": start_time,
            "end_time": start_time + MINUTE,
            "reason": "VeryReason",
            "detail": "so detail",
        }
    return None


StringTableElem = Mapping[str, Mapping[object, Mapping[str, object]]]


@pytest.fixture
def string_table_element(
    container_name: str, container_state_dict: Mapping[str, str | int], num_of_containers: int
) -> StringTableElem:
    return {
        "containers": {
            container_name.format(i): {
                "container_id": "docker://fcde010771eafc68bb644d180808d0f3f3f93c04a627a7cc53cb255efad99c5a",
                "image_id": "some-id",
                "name": container_name.format(i),
                "image": "checkmk/worker_agent:0.4",
                "ready": True,
                "state": container_state_dict,
                "restart_count": 3,
            }
            for i in range(num_of_containers)
        }
    }


@pytest.fixture
def string_table(string_table_element: StringTableElem) -> StringTable:
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    return kube_pod_containers.parse(string_table)


@pytest.fixture
def failed_state():
    return int(State.CRIT)


@pytest.fixture
def params(failed_state):
    return {"failed_state": failed_state}


@pytest.fixture
def check_result(container_name, params, section):
    return kube_pod_containers._check(TIMESTAMP, container_name, params, section)


def test_parse(
    container_name: str, container_state: ContainerStateType, string_table: StringTable
) -> None:
    section = kube_pod_containers.parse(string_table)
    assert section is not None
    assert container_name in section.containers
    assert section.containers[container_name].state.type == container_state


@pytest.mark.parametrize("num_of_containers", [1, 2, 5, 10])
def test_discovery_returns_as_much_services_as_containers(
    num_of_containers: int, section: PodContainers
) -> None:
    assert len(list(kube_pod_containers.discovery(section))) == num_of_containers


def test_check_yields_check_single_result(check_result: CheckResult) -> None:
    assert len(list(check_result)) == 3


def test_check_result_state_ok(check_result: CheckResult) -> None:
    assert all(isinstance(result, Result) and result.state == State.OK for result in check_result)


def test_check_result_summary_status(check_result: CheckResult) -> None:
    result, _, _ = check_result
    assert isinstance(result, Result)
    assert result.summary == "Status: Running for 0 seconds"


def test_check_result_summary_image(
    container_name: str, string_table_element: StringTableElem, check_result: CheckResult
) -> None:
    expected_summary = f"Image: {string_table_element['containers'][container_name]['image']}"
    _, result, _ = check_result
    assert isinstance(result, Result)
    assert result.summary == expected_summary


def test_check_result_summary_restart_count(
    container_name: str, string_table_element: StringTableElem, check_result: CheckResult
) -> None:
    expected_summary = (
        f"Restart count: {string_table_element['containers'][container_name]['restart_count']}"
    )
    _, _, result = check_result
    assert isinstance(result, Result)
    assert result.summary == expected_summary


@pytest.mark.parametrize("timespan", [1 * MINUTE, 2 * MINUTE, 5 * MINUTE])
def test_check_result_summary_start_time(timespan: float, check_result: CheckResult) -> None:
    expected_timespan = render.timespan(timespan)
    result, _, _ = check_result
    assert isinstance(result, Result)
    assert result.summary == f"Status: Running for {expected_timespan}"


@pytest.mark.parametrize("container_state", ["waiting"])
def test_check_result_waiting(check_result: CheckResult) -> None:
    result, _, _ = check_result
    assert isinstance(result, Result)
    assert result.state == State.OK
    assert result.summary == "Status: Waiting (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
def test_check_result_terminated_status(
    check_result: CheckResult,
) -> None:
    result, _, _, _ = check_result
    assert isinstance(result, Result)
    assert result.state == State.OK
    assert result.summary == "Status: Succeeded (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
def test_check_result_terminated_end_time(start_time: float, check_result: CheckResult) -> None:
    expected_end_time = render.datetime(start_time + MINUTE)
    expected_duration = render.timespan(MINUTE)
    _, result, _, _ = check_result
    assert isinstance(result, Result)
    assert result.state == State.OK
    assert result.summary == f"End time: {expected_end_time} Run duration: {expected_duration}"


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
def test_check_result_terminated_non_zero_exit_code_status(
    check_result: CheckResult,
) -> None:
    result, _, _, _ = check_result
    assert isinstance(result, Result)
    assert result.state == State.CRIT
    assert result.summary == "Status: Failed (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
@pytest.mark.parametrize(
    "failed_state", [int(State.OK), int(State.WARN), int(State.CRIT), int(State.UNKNOWN)]
)
def test_check_result_terminated_non_zero_exit_code_status_specified_params(
    failed_state, check_result
):
    result, _, _, _ = check_result
    assert result.state == State(failed_state)
    assert result.summary == "Status: Failed (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
@pytest.mark.parametrize("params", [{}])
def test_check_result_terminated_non_zero_exit_code_no_params_raises(
    check_result: CheckResult,
) -> None:
    with pytest.raises(KeyError):
        list(check_result)


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
@pytest.mark.parametrize("failed_state", [179])
def test_check_result_terminated_non_zero_exit_code_invalid_state_raises(
    check_result: CheckResult,
) -> None:
    with pytest.raises(ValueError):
        list(check_result)


class ContainerTerminatedStateFactory(ModelFactory):
    __model__ = ContainerTerminatedState


def test_container_terminated_state_with_no_start_and_end_times() -> None:
    terminated_container_state = ContainerTerminatedStateFactory.build(
        exit_code=0,
        start_time=None,
        end_time=None,
    )
    result = list(
        kube_pod_containers.check_terminated(
            {"failed_state": int(State.CRIT)}, terminated_container_state
        )
    )

    assert [r.state for r in result if isinstance(r, Result)] == [State.OK]


def test_container_terminated_state_with_only_start_time() -> None:
    terminated_container_state = ContainerTerminatedStateFactory.build(
        exit_code=0,
        start_time=TIMESTAMP,
        end_time=None,
        reason="reason",
        detail="detail",
    )

    result = list(
        kube_pod_containers.check_terminated(
            {"failed_state": int(State.CRIT)}, terminated_container_state
        )
    )

    assert [r.state for r in result if isinstance(r, Result)] == [State.OK, State.OK]
    assert [r.summary for r in result if isinstance(r, Result)] == [
        "Status: Succeeded (reason: detail)",
        f"Start time: {render.datetime(TIMESTAMP)}",
    ]


def test_container_terminated_state_linebreak_in_detail() -> None:
    terminated_container_state = ContainerTerminatedStateFactory.build(
        exit_code=0,
        start_time=TIMESTAMP,
        end_time=TIMESTAMP + 1,
        reason="Completed",
        detail="Installing helm_v3 chart\n",
    )

    result = list(kube_pod_containers.check_terminated({}, terminated_container_state))

    assert all(r.state == State.OK for r in result if isinstance(r, Result))
    assert any(
        r.summary.startswith(r"Status: Succeeded (Completed: Installing helm_v3 chart)")
        for r in result
        if isinstance(r, Result)
    )


def test_container_terminated_state_no_detail() -> None:
    terminated_container_state = ContainerTerminatedStateFactory.build(
        exit_code=0,
        start_time=TIMESTAMP,
        end_time=TIMESTAMP + 1,
        reason="Completed",
        detail=None,
    )

    result = list(kube_pod_containers.check_terminated({}, terminated_container_state))

    assert all(r.state == State.OK for r in result if isinstance(r, Result))
    assert any(
        r.summary.startswith(r"Status: Succeeded (Completed: None)")
        for r in result
        if isinstance(r, Result)
    )
