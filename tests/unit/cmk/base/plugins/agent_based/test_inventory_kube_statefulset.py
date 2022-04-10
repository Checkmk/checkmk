#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_statefulset import inventory_kube_statefulset
from cmk.base.plugins.agent_based.utils.kube import (
    Recreate,
    Selector,
    StatefulSetInfo,
    StatefulSetRollingUpdate,
    ThinContainers,
    UpdateStrategy,
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
                containers=ThinContainers(images={"i/name:0.5"}, names=["name"]),
                cluster="cluster",
            ),
            UpdateStrategy(strategy=StatefulSetRollingUpdate(partition=0)),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "StatefulSet",
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "statefulset"],
                    inventory_attributes={
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
    section_strategy: UpdateStrategy,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventory_kube_statefulset(section_info, section_strategy)
    ) == sort_inventory_result(expected_inventory_result)


def test_inventory_kube_statefulset_calls_labels_to_table(mocker):
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class StatefulSetInfoFactory(ModelFactory):
        __model__ = StatefulSetInfo
        selector = Selector(match_labels={}, match_expressions=[])

    section_info = StatefulSetInfoFactory.build()

    section_strategy = UpdateStrategy(strategy=Recreate())

    mock = mocker.patch("cmk.base.plugins.agent_based.inventory_kube_statefulset.labels_to_table")
    list(inventory_kube_statefulset(section_info, section_strategy))
    mock.assert_called_once()
