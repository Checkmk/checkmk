#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_daemonset_info import check_kube_daemonset_info
from cmk.base.plugins.agent_based.utils import kube_info
from cmk.base.plugins.agent_based.utils.kube import DaemonSetInfo, Selector, ThinContainers


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            DaemonSetInfo(
                name="oh-lord",
                namespace="have-mercy",
                labels={},
                annotations={},
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=1600000000.0,
                containers=ThinContainers(images={"i/name:0.5"}, names=["name"]),
                cluster="cluster",
            ),
            (
                Result(state=State.OK, summary="Name: oh-lord"),
                Result(state=State.OK, summary="Namespace: have-mercy"),
                Result(state=State.OK, summary="Age: 1 second"),
            ),
            id="overall look of DaemonSet with age 1 second",
        ),
    ],
)
def test_check_kube_daemonset_info(  # type:ignore[no-untyped-def]
    section: DaemonSetInfo, expected_check_result: Tuple[Result, ...], mocker
) -> None:
    with mocker.patch.object(kube_info.time, "time", return_value=1600000001.0):
        assert tuple(check_kube_daemonset_info(section)) == expected_check_result
