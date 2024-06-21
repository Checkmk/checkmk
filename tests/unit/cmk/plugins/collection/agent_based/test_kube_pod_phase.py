#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_pod_phase import check_kube_pod_phase
from cmk.plugins.kube.schemata.api import Phase
from cmk.plugins.kube.schemata.section import PodLifeCycle


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            PodLifeCycle(phase=Phase.RUNNING),
            (Result(state=State.OK, summary="Running"),),
            id="running",
        ),
    ],
)
def test_check_kube_pod_phase(
    section: PodLifeCycle,
    expected_result: tuple[Result],
) -> None:
    assert expected_result == tuple(check_kube_pod_phase(section))
