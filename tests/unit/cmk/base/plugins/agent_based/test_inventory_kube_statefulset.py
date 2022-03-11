#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_statefulset import inventory_kube_statefulset
from cmk.base.plugins.agent_based.utils.k8s import (
    Selector,
    StatefulSetInfo,
    StatefulSetRollingUpdate,
    StatefulSetStrategy,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_inventory_result",
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
            StatefulSetStrategy(strategy=StatefulSetRollingUpdate(partition=0)),
            [
                Attributes(
                    path=["software", "applications", "kube", "statefulset"],
                    inventory_attributes={
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                        "strategy": "RollingUpdate (partitioned at: 0)",
                        "match_labels": "",
                        "match_expressions": "",
                    },
                    status_attributes={},
                ),
            ],
            id="overall look of StatefulSet inventory",
        ),
    ],
)
def test_inventory_kube_statefulset(
    section_info: StatefulSetInfo,
    section_strategy: StatefulSetStrategy,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventory_kube_statefulset(section_info, section_strategy)
    ) == sort_inventory_result(expected_inventory_result)
