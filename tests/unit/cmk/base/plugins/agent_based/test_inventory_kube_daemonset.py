#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_daemonset import inventory_kube_daemonset
from cmk.base.plugins.agent_based.utils.kube import (
    DaemonSetInfo,
    DaemonSetStrategy,
    RollingUpdate,
    Selector,
    ThinContainers,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_inventory_result",
    [
        pytest.param(
            DaemonSetInfo(
                name="oh-lord",
                namespace="have-mercy",
                labels={},
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=1600000000.0,
                containers=ThinContainers(images={"i/name:0.5"}, names=["name"]),
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


def test_inventory_kube_daemonset_calls_labels_to_table(mocker):
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class DaemonSetInfoFactory(ModelFactory):
        __model__ = DaemonSetInfo
        selector = Selector(match_labels={}, match_expressions=[])

    section_info = DaemonSetInfoFactory.build()

    class DaemonSetStrategyFactory(ModelFactory):
        __model__ = DaemonSetStrategy

    section_strategy = DaemonSetStrategyFactory.build()

    mock = mocker.patch("cmk.base.plugins.agent_based.inventory_kube_daemonset.labels_to_table")
    list(inventory_kube_daemonset(section_info, section_strategy))
    mock.assert_called_once()
