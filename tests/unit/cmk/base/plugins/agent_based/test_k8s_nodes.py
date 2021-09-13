#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.k8s_nodes import check_k8s_nodes


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        (
            {
                "nodes": [
                    "ip-192-168-17-38.eu-central-1.compute.internal",
                    "ip-192-168-79-29.eu-central-1.compute.internal",
                ],
            },
            {
                "levels": (10, 11),
                "levels_lower": (4, 3),
            },
            [
                Result(state=State.CRIT, summary="Number of nodes: 2 (warn/crit below 4/3)"),
                Metric("k8s_nodes", 2.0, levels=(10.0, 11.0), boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_k8s_nodes(section, params, expected_result):
    result = list(check_k8s_nodes(params, section))
    assert result == expected_result
