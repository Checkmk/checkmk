#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_statefulset_info import (
    check_kube_statefulset_info,
    StatefulSetInfo,
)
from cmk.base.plugins.agent_based.utils import kube_info
from cmk.base.plugins.agent_based.utils.k8s import Selector


# TODO: CMK-10052
@pytest.fixture(name="time")
def fixture_time(mocker):
    import time as time_mock

    time_mock.time = mocker.Mock(return_value=1600000001.0)
    mocker.patch.object(kube_info, "time", time_mock)
    return time_mock


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            StatefulSetInfo(
                name="oh-lord",
                namespace="have-mercy",
                labels={},
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=1600000000.0,
                cluster="cluster",
            ),
            (
                Result(state=State.OK, summary="Name: oh-lord"),
                Result(state=State.OK, summary="Namespace: have-mercy"),
                Result(state=State.OK, summary="Age: 1 second"),
            ),
            id="overall look of StatefulSet with age 1 second",
        ),
    ],
)
def test_check_kube_statefulset_info(
    section: StatefulSetInfo, expected_check_result: Tuple[Result, ...], time
) -> None:
    assert tuple(check_kube_statefulset_info(section)) == expected_check_result
