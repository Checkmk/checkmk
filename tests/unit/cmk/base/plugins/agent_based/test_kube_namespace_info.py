#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_namespace_info import check_kube_namespace_info
from cmk.base.plugins.agent_based.utils import kube_info
from cmk.base.plugins.agent_based.utils.kube import NamespaceInfo


@pytest.fixture(name="time")
def fixture_time(mocker):
    import time as time_mock

    time_mock.time = mocker.Mock(return_value=1600000001.0)
    mocker.patch.object(kube_info, "time", time_mock)
    return time_mock


def test_check_kube_node_info(time) -> None:
    info = NamespaceInfo(
        name="namespace",
        creation_timestamp=1600000000.0,
        labels={},
        cluster="cluster",
    )
    check_result = check_kube_namespace_info(info)
    assert list(check_result) == [
        Result(state=State.OK, summary="Name: namespace"),
        Result(state=State.OK, summary="Age: 1 second"),
    ]
