#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest

from cmk.base.plugins.agent_based import kube_pod_restarts
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.utils.k8s import PodContainers

from cmk.gui.plugins.wato.check_parameters.kube_pod_restarts import _parameter_valuespec

ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE
TIMESTAMP = 359

OK = 1  # value for restarts of each container to set state to OK
WARN = 10  # value for restarts of each container to set state to WARN
CRIT = 100  # value for restarts of each container to set state to CRIT
NUMBER_OF_CONTAINERS = 10  # default value for number of containers

# default values for upper levels
RESTART_COUNT_LEVELS = WARN * NUMBER_OF_CONTAINERS, CRIT * NUMBER_OF_CONTAINERS
RESTART_RATE_LEVELS = WARN * NUMBER_OF_CONTAINERS * 60, CRIT * NUMBER_OF_CONTAINERS * 60


@pytest.fixture(autouse=True)
def time(mocker):
    def time_side_effect():
        timestamp = TIMESTAMP
        while True:
            yield timestamp
            timestamp += ONE_MINUTE

    time_mock = mocker.Mock(side_effect=time_side_effect())
    mocker.patch.object(kube_pod_restarts, "time", mocker.Mock(time=time_mock))
    return time_mock


@pytest.fixture
def restart_count():
    return OK


@pytest.fixture
def string_table_element(restart_count):
    return {
        "containers": {
            f"doge-{i}": {
                "container_id": "docker://fcde010771eafc68bb644d180808d0f3f3f93c04a627a7cc53cb255efad99c5a",
                "image_id": "some-id",
                "name": f"doge-{i}",
                "image": "tribe29/worker_agent:0.4",
                "ready": True,
                "state": {"type": "running", "start_time": 359},
                "restart_count": restart_count,
            }
            for i in range(NUMBER_OF_CONTAINERS)
        }
    }


@pytest.fixture
def string_table(string_table_element):
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    if not string_table:
        return None
    return PodContainers(**json.loads(string_table[0][0]))


@pytest.fixture
def params():
    return kube_pod_restarts.Params(
        restart_count=("levels", RESTART_COUNT_LEVELS),
        restart_rate=("levels", RESTART_RATE_LEVELS),
    )


@pytest.fixture
def check_result(params, section):
    return kube_pod_restarts.check(params, section)


@pytest.fixture
def expired_values():
    return 1


@pytest.fixture
def current_values():
    return ONE_HOUR // ONE_MINUTE - 1


@pytest.fixture
def is_empty_value_store():
    return False


@pytest.fixture
def value_store(expired_values, current_values, restart_count, is_empty_value_store):
    if is_empty_value_store:
        return {}
    n = ONE_HOUR // ONE_MINUTE + expired_values
    restart_count_list = [
        (TIMESTAMP - (n - i) * ONE_MINUTE, restart_count * (-n + i) * NUMBER_OF_CONTAINERS)
        for i in range(expired_values)
    ]
    n = current_values
    restart_count_list += [
        (TIMESTAMP - (n - i) * ONE_MINUTE, restart_count * (-n + i) * NUMBER_OF_CONTAINERS)
        for i in range(current_values)
    ]
    return {"restart_count_list": restart_count_list}


@pytest.fixture(autouse=True)
def get_value_store(value_store, mocker):
    mock = mocker.Mock(return_value=value_store)
    mocker.patch.object(kube_pod_restarts, "get_value_store", mock)
    return mock


def test_discovery_returns_single_service(section):
    assert len(list(kube_pod_restarts.discovery(section))) == 1


def test_check_yields_two_results(check_result):
    assert len([r for r in check_result if isinstance(r, Result)]) == 2


def test_check_results_state_ok(check_result):
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


def test_check_result_summary(check_result):
    expected = [
        f"Total: {OK * NUMBER_OF_CONTAINERS}",
        f"In last hour: {OK * NUMBER_OF_CONTAINERS * ONE_HOUR // ONE_MINUTE}",
    ]
    actual = [r.summary for r in check_result if isinstance(r, Result)]
    assert actual == expected


@pytest.mark.parametrize("restart_count", [WARN, CRIT])
def test_check_result_summary_alert(restart_count, params, check_result):
    warn_crit_count = "(warn/crit at {}/{})".format(*params["restart_count"][1])
    warn_crit_rate = "(warn/crit at {}/{})".format(*params["restart_rate"][1])
    expected = [
        f"Total: {restart_count * NUMBER_OF_CONTAINERS} {warn_crit_count}",
        f"In last hour: {restart_count * NUMBER_OF_CONTAINERS * ONE_HOUR // ONE_MINUTE} {warn_crit_rate}",
    ]
    actual = [r.summary for r in check_result if isinstance(r, Result)]
    assert actual == expected


def test_check_yields_two_metrics(check_result):
    assert len([m for m in check_result if isinstance(m, Metric)]) == 2


def test_check_metric_value(check_result):
    expected = [OK * NUMBER_OF_CONTAINERS, OK * NUMBER_OF_CONTAINERS * ONE_HOUR // ONE_MINUTE]
    actual = [int(m.value) for m in check_result if isinstance(m, Metric)]
    assert actual == expected


@pytest.mark.parametrize(
    "restart_count, expected_states",
    [
        (OK, [State.OK, State.OK]),
        (WARN, [State.WARN, State.WARN]),
        (CRIT, [State.CRIT, State.CRIT]),
    ],
)
def test_check_result_state_mixed(expected_states, check_result):
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


@pytest.mark.parametrize("expired_values", [0, 10, 30, 50, 59])
@pytest.mark.parametrize("current_values", [10, 30, 50, 59])
def test_check_results_considers_only_current_values(current_values, check_result):
    expected = [OK * NUMBER_OF_CONTAINERS, OK * NUMBER_OF_CONTAINERS * (current_values + 1)]
    actual = [int(m.value) for m in check_result if isinstance(m, Metric)]
    assert actual == expected


@pytest.mark.parametrize("expired_values", [0, 10, 30, 50, 59])
@pytest.mark.parametrize("current_values", [0])
def test_check_yields_single_result_when_no_current_values(current_values, check_result):
    expected = [OK * NUMBER_OF_CONTAINERS]
    actual = [int(m.value) for m in check_result if isinstance(m, Metric)]
    assert actual == expected


@pytest.mark.parametrize("is_empty_value_store", [True])
def test_check_results_creates_restart_count_list(value_store, check_result):
    list(check_result)
    assert len(value_store) == 1
    assert "restart_count_list" in value_store
    assert len(value_store["restart_count_list"]) == 1
    assert value_store["restart_count_list"][0] == (TIMESTAMP, OK * NUMBER_OF_CONTAINERS)


def test_check_results_updates_restart_count_list(value_store, check_result):
    list(check_result)
    assert len(value_store["restart_count_list"]) == ONE_HOUR // ONE_MINUTE
    assert value_store["restart_count_list"][-1] == (TIMESTAMP, OK * NUMBER_OF_CONTAINERS)


@pytest.mark.parametrize("expired_values", [0, 10, 100])
def test_check_results_disregards_expired_values(value_store, check_result):
    list(check_result)
    assert len(value_store["restart_count_list"]) == ONE_HOUR // ONE_MINUTE


@pytest.mark.parametrize("expired_values", [0, 10, 100])
def test_check_results_maintains_restart_count_list_sorted(value_store, check_result):
    list(check_result)
    assert value_store["restart_count_list"] == sorted(value_store["restart_count_list"])


def test_valuespec_and_check_agree() -> None:
    assert tuple(kube_pod_restarts._DEFAULT_PARAMS) == tuple(
        element[0] for element in _parameter_valuespec()._get_elements()
    )
