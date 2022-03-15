#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_deployment import inventory_kube_deployment
from cmk.base.plugins.agent_based.utils.kube import (
    DeploymentInfo,
    DeploymentStrategy,
    RollingUpdate,
    Selector,
    ThinContainers,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_check_result",
    [
        pytest.param(
            DeploymentInfo(
                name="oh-lord",
                namespace="have-mercy",
                labels={},
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=1600000000.0,
                containers=ThinContainers(images={"i/name:0.5"}, names=["name"]),
                cluster="cluster",
            ),
            DeploymentStrategy(
                strategy=RollingUpdate(
                    max_surge="25%",
                    max_unavailable="25%",
                )
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "deployment"],
                    inventory_attributes={
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                        "strategy": "RollingUpdate (max surge: 25%, max unavailable: 25%)",
                        "match_labels": "",
                        "match_expressions": "",
                    },
                    status_attributes={},
                ),
            ],
            id="overall look of deployment inventory",
        ),
    ],
)
def test_inventory_kube_deployment(
    section_info: DeploymentInfo,
    section_strategy: DeploymentStrategy,
    expected_check_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventory_kube_deployment(section_info, section_strategy)
    ) == sort_inventory_result(expected_check_result)
