#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Tuple

import pytest

from cmk.base.plugins.agent_based import kube_pod_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_pod_info import (
    _DETAILS_ONLY,
    _DISPLAY_NAME,
    check_kube_pod_info,
    PodInfo,
)


@pytest.fixture(name="time")
def fixture_time(mocker):
    import time as time_mock

    time_mock.time = mocker.Mock(return_value=1600000001.0)
    mocker.patch.object(kube_pod_info, "time", time_mock)
    return time_mock


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            PodInfo(
                namespace="default",
                creation_timestamp=1600000000.0,
                labels={},
                node=None,
                qos_class="burstable",
                restart_policy="Always",
                uid="dd1019ca-c429-46af-b6b7-8aad47b6081a",
            ),
            (
                Result(state=State.OK, summary="Node: None"),
                Result(state=State.OK, summary="Namespace: default"),
                Result(state=State.OK, summary="Age: 1 second"),
                Result(state=State.OK, notice="QoS class: burstable"),
                Result(state=State.OK, notice="UID: dd1019ca-c429-46af-b6b7-8aad47b6081a"),
                Result(state=State.OK, notice="Restart policy: Always"),
            ),
            id="overall look of pod with age 1 second",
        ),
    ],
)
def test_check_kube_pod_info(
    section: PodInfo, expected_check_result: Tuple[Result, ...], time
) -> None:
    assert tuple(check_kube_pod_info(section)) == expected_check_result


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param(
            _DETAILS_ONLY,
            id="_DETAILS_ONLY elements are found in Pod Info",
        ),
        pytest.param(
            _DISPLAY_NAME,
            id="_DISPLAY_NAME keys are found in Pod Info",
        ),
    ],
)
def test_subset_fields_used_by_check_pod_info(fields: Iterable[str]) -> None:
    """
    The function check_kube_pod_info uses the variables _DETAILS_ONLY and _DISPLAY_NAME, which
    make assumptions, which fields are present in the class PodInfo. Since PodInfo might need be
    changed in response to Kubernetes API updates, we test the validity of those variables.
    """
    for field in fields:
        assert field in PodInfo.__fields__
