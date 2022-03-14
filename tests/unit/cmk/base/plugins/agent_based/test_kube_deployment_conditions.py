#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json
from typing import Any, Mapping, Optional, Union

import pytest

from cmk.base.plugins.agent_based import kube_deployment_conditions
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable
from cmk.base.plugins.agent_based.utils.kube import DeploymentConditions, VSResultAge

MINUTE = 60
TIMESTAMP = 120

OK = 0
WARN = 10
CRIT = 20


def condition_true(time_diff_minutes: int = 0) -> Mapping[str, Union[str, int]]:
    return {
        "status": "True",
        "reason": "reason",
        "message": "message",
        "last_transition_time": TIMESTAMP - time_diff_minutes * MINUTE,
    }


def condition_false(time_diff_minutes: int = 0) -> Mapping[str, Union[str, int]]:
    return {
        "status": "False",
        "reason": "reason",
        "message": "message",
        "last_transition_time": TIMESTAMP - time_diff_minutes * MINUTE,
    }


@pytest.fixture(autouse=True)
def time(mocker):
    def time_call():
        timestamp = TIMESTAMP
        while True:
            yield timestamp

    time_mock = mocker.Mock(side_effect=time_call())
    mocker.patch.object(kube_deployment_conditions, "time", mocker.Mock(time=time_mock))
    return time_mock


@pytest.fixture
def params() -> Mapping[str, VSResultAge]:
    return dict(
        progressing=("levels", (WARN * MINUTE, CRIT * MINUTE)),
        available=("levels", (WARN * MINUTE, CRIT * MINUTE)),
        replicafailure=("levels", (WARN * MINUTE, CRIT * MINUTE)),
    )


@pytest.fixture
def state() -> int:
    return OK


@pytest.fixture
def state_progressing(state: int) -> int:
    return state


@pytest.fixture
def state_available(state: int) -> int:
    return state


@pytest.fixture
def state_replicafailure(state: int) -> int:
    return state


@pytest.fixture
def status_progressing() -> Optional[bool]:
    return True


@pytest.fixture
def status_available() -> Optional[bool]:
    return True


@pytest.fixture
def status_replicafailure() -> Optional[bool]:
    return False


@pytest.fixture
def string_table_element(
    status_progressing: Optional[bool],
    state_progressing: int,
    status_available: Optional[bool],
    state_available: int,
    status_replicafailure: Optional[bool],
    state_replicafailure: int,
) -> Mapping[str, Any]:
    return {
        "progressing": None
        if status_progressing is None
        else (
            condition_true(state_progressing)
            if status_progressing
            else condition_false(state_progressing)
        ),
        "available": None
        if status_available is None
        else (
            condition_true(state_available)
            if status_available
            else condition_false(state_available)
        ),
        "replicafailure": None
        if status_replicafailure is None
        else (
            condition_true(state_replicafailure)
            if status_replicafailure
            else condition_false(state_replicafailure)
        ),
    }


@pytest.fixture
def string_table(string_table_element: Mapping[str, Any]) -> StringTable:
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table: StringTable) -> DeploymentConditions:
    return kube_deployment_conditions.parse(string_table)


@pytest.fixture
def check_result(params: Mapping[str, VSResultAge], section: DeploymentConditions) -> CheckResult:
    return kube_deployment_conditions.check(params, section)


def test_ok_state_mappings_match_conditions():
    assert all(
        condition in kube_deployment_conditions.CONDITIONS_OK_MAPPINGS
        for condition in DeploymentConditions.schema()["properties"]
    )


def test_parse(string_table: StringTable):
    section = kube_deployment_conditions.parse(string_table)
    assert section is not None
    assert len(section.dict()) == 3


def test_discovery(section: DeploymentConditions):
    discovered_services = list(kube_deployment_conditions.discovery(section))
    assert len(discovered_services) == 1


def test_all_ok_check_result(check_result: CheckResult):
    assert len(list(check_result)) == 1


@pytest.mark.parametrize("status_replicafailure", [None])
def test_no_replicafailure_and_others_ok_check_result(check_result: CheckResult):
    results = list(check_result)
    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK


@pytest.mark.parametrize("status_replicafailure", [None])
@pytest.mark.parametrize("state", [WARN])
@pytest.mark.parametrize("status_progressing, status_available", [(True, False), (False, True)])
def test_no_replicafailure_and_one_false_condition_check_result(check_result: CheckResult):
    results = list(check_result)
    assert len(results) == 2
    assert (
        len(
            [
                result
                for result in results
                if isinstance(result, Result) and result.state == State.OK
            ]
        )
        == 1
    )
    assert (
        len(
            [
                result
                for result in results
                if isinstance(result, Result) and result.state == State.WARN
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "status_replicafailure, status_progressing, state_available", [(True, False, False)]
)
def test_all_failing_status_but_within_valid_time_range(check_result: CheckResult):
    results = list(check_result)
    assert len(results) == 3
    assert all(result.state == State.OK for result in results if isinstance(result, Result))


@pytest.mark.parametrize(
    "status_replicafailure, status_progressing, status_available", [(True, False, False)]
)
@pytest.mark.parametrize("params", [{}])
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_result_all_failing_but_with_no_params(check_result: CheckResult):
    results = list(check_result)
    assert all(isinstance(result, Result) for result in results)
    assert all(result.state == State.OK for result in results if isinstance(result, Result))


@pytest.mark.parametrize("status_replicafailure, status_available", [(None, None)])
@pytest.mark.parametrize("status_progressing, state_progressing", [(False, WARN)])
def test_failing_condition_with_warn_time_difference(check_result: CheckResult):
    results = list(check_result)
    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].summary.startswith("PROGRESSING: False (reason: message)")
