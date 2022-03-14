#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_pod_phase import check_kube_pod_phase
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            PodLifeCycle(phase="running"),
            (Result(state=State.OK, summary="Running"),),
            id="running",
        ),
    ],
)
def test_check_kube_pod_phase(section: PodLifeCycle, expected_result) -> None:
    assert expected_result == tuple(check_kube_pod_phase(section))
