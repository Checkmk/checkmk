#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_kube_daemonset import inventory_kube_daemonset
from cmk.base.plugins.agent_based.utils.k8s import (
    DaemonSetInfo,
    DaemonSetStrategy,
    Label,
    LabelName,
    RollingUpdate,
    Selector,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_inventory_result",
    [
        pytest.param(
            DaemonSetInfo(
                name="oh-lord",
                namespace="have-mercy",
                labels={LabelName("app"): Label(name="app", value="checkmk-cluster-agent")},
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=1600000000.0,
                cluster="cluster",
            ),
            DaemonSetStrategy(
                strategy=RollingUpdate(
                    max_surge="0",
                    max_unavailable="1",
                )
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "daemonset"],
                    inventory_attributes={
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                        "strategy": "RollingUpdate (max surge: 0, max unavailable: 1)",
                        "match_labels": "",
                        "match_expressions": "",
                    },
                    status_attributes={},
                ),
                TableRow(
                    path=["software", "applications", "kube", "labels"],
                    key_columns={"label_name": "app"},
                    inventory_columns={"label_value": "checkmk-cluster-agent"},
                    status_columns={},
                ),
            ],
            id="overall look of DaemonSet inventory",
        ),
    ],
)
def test_inventory_kube_daemonset(
    section_info: DaemonSetInfo,
    section_strategy: DaemonSetStrategy,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventory_kube_daemonset(section_info, section_strategy)
    ) == sort_inventory_result(expected_inventory_result)
