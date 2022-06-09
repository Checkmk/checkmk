#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based import kube_pod_containers
from cmk.base.plugins.agent_based.agent_based_api.v1 import render, Result, State
from cmk.base.plugins.agent_based.utils.kube import ContainerTerminatedState

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


@pytest.fixture
def string_table_element(container_name, container_state_dict, num_of_containers):
    return {
        "containers": {
            container_name.format(i): {
                "container_id": "docker://fcde010771eafc68bb644d180808d0f3f3f93c04a627a7cc53cb255efad99c5a",
                "image_id": "some-id",
                "name": container_name.format(i),
                "image": "tribe29/worker_agent:0.4",
                "ready": True,
                "state": container_state_dict,
                "restart_count": 3,
            }
            for i in range(num_of_containers)
        }
    }


@pytest.fixture
def string_table(string_table_element):
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    return kube_pod_containers.parse(string_table)


@pytest.fixture(autouse=True)
def time(mocker):
    def time_side_effect():
        timestamp = TIMESTAMP
        while True:
            yield timestamp
            timestamp += MINUTE

    time_mock = mocker.Mock(side_effect=time_side_effect())
    mocker.patch.object(kube_pod_containers, "time", time_mock)
    return time_mock


@pytest.fixture
def failed_state():
    return int(State.CRIT)


@pytest.fixture
def params(failed_state):
    return {"failed_state": failed_state}


@pytest.fixture
def check_result(container_name, params, section):
    return kube_pod_containers.check(container_name, params, section)


def test_parse(container_name, container_state, string_table):
    section = kube_pod_containers.parse(string_table)
    assert section is not None
    assert container_name in section.containers
    assert section.containers[container_name].state.type == container_state


@pytest.mark.parametrize("num_of_containers", [1, 2, 5, 10])
def test_discovery_returns_as_much_services_as_containers(num_of_containers, section):
    assert len(list(kube_pod_containers.discovery(section))) == num_of_containers


def test_check_yields_check_single_result(check_result):
    assert len(list(check_result)) == 3


def test_check_result_state_ok(check_result):
    assert all(result.state == State.OK for result in check_result)


def test_check_result_summary_status(check_result):
    result, _, _ = check_result
    assert result.summary == "Status: Running for 0 seconds"


def test_check_result_summary_image(container_name, string_table_element, check_result):
    expected_summary = f"Image: {string_table_element['containers'][container_name]['image']}"
    _, result, _ = check_result
    assert result.summary == expected_summary


def test_check_result_summary_restart_count(container_name, string_table_element, check_result):
    expected_summary = (
        f"Restart count: {string_table_element['containers'][container_name]['restart_count']}"
    )
    _, _, result = check_result
    assert result.summary == expected_summary


@pytest.mark.parametrize("timespan", [1 * MINUTE, 2 * MINUTE, 5 * MINUTE])
def test_check_result_summary_start_time(timespan, check_result):
    expected_timespan = render.timespan(timespan)
    result, _, _ = check_result
    assert result.summary == f"Status: Running for {expected_timespan}"


@pytest.mark.parametrize("container_state", ["waiting"])
def test_check_result_waiting(check_result):
    result, _, _ = check_result
    assert result.state == State.OK
    assert result.summary == "Status: Waiting (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
def test_check_result_terminated_status(check_result):
    result, _, _, _ = check_result
    assert result.state == State.OK
    assert result.summary == "Status: Succeeded (VeryReason: so detail)"


@pytest.mark.parametrize("container_state", ["terminated"])
def test_check_result_terminated_end_time(start_time, check_result):
    expected_end_time = render.datetime(start_time + MINUTE)
    expected_duration = render.timespan(MINUTE)
    _, result, _, _ = check_result
    assert result.state == State.OK
    assert result.summary == f"End time: {expected_end_time} Run duration: {expected_duration}"


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
def test_check_result_terminated_non_zero_exit_code_status(check_result):
    result, _, _, _ = check_result
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
def test_check_result_terminated_non_zero_exit_code_no_params_raises(check_result):
    with pytest.raises(KeyError):
        list(check_result)


@pytest.mark.parametrize("container_state", ["terminated"])
@pytest.mark.parametrize("exit_code", [1])
@pytest.mark.parametrize("failed_state", [179])
def test_check_result_terminated_non_zero_exit_code_invalid_state_raises(check_result):
    with pytest.raises(ValueError):
        list(check_result)


class ContainerTerminatedStateFactory(ModelFactory):
    __model__ = ContainerTerminatedState


def test_container_terminated_state_with_no_start_and_end_times():
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


def test_container_terminated_state_with_only_start_time():
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
