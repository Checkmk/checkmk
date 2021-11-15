#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.k8s_node_kubelet import check_k8s_node_kubelet
from cmk.base.plugins.agent_based.utils.k8s import HealthZ, KubeletInfo


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                health=HealthZ(status_code=200, response="ok", verbose_response=None),
            ),
            [
                Result(state=State.OK, summary="Version 1.2.3"),
                Result(state=State.OK, summary="Health check response is ok"),
            ],
            id="status_code_ok",
        ),
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                health=HealthZ(
                    status_code=500, response="bad", verbose_response="some\nlong\noutput\n"
                ),
            ),
            [
                Result(state=State.OK, summary="Version 1.2.3"),
                Result(
                    state=State.CRIT,
                    summary="Health check response is bad",
                    details="some\nlong\noutput\n",
                ),
            ],
            id="status_code_critical",
        ),
    ],
)
def test_check_k8s_node_kubelet(section: KubeletInfo, expected_result) -> None:
    result = list(check_k8s_node_kubelet(section))
    assert result == expected_result
