#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_node_kubelet import check_kube_node_kubelet
from cmk.base.plugins.agent_based.utils.kube import HealthZ, KubeletInfo


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=HealthZ(status_code=200, response="ok", verbose_response=None),
            ),
            [
                Result(state=State.OK, summary="Healthy"),
                Result(state=State.OK, summary="Version 1.2.3"),
            ],
            id="status_code_ok",
        ),
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=HealthZ(
                    status_code=500, response="bad", verbose_response="some\nlong\noutput\n"
                ),
            ),
            [
                Result(state=State.CRIT, summary="Not healthy"),
                Result(
                    state=State.OK,
                    notice="Verbose response:\nsome\nlong\noutput\n",
                ),
                Result(state=State.OK, summary="Version 1.2.3"),
            ],
            id="status_code_critical",
        ),
    ],
)
def test_check_kube_node_kubelet(section: KubeletInfo, expected_result) -> None:
    result = list(check_kube_node_kubelet(section))
    assert result == expected_result
