#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_kube_daemonset import inventory_kube_daemonset
from cmk.plugins.kube.schemata.api import (
    ContainerName,
    NamespaceName,
    OnDelete,
    RollingUpdate,
    Selector,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import (
    DaemonSetInfo,
    FilteredAnnotations,
    ThinContainers,
    UpdateStrategy,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_inventory_result",
    [
        pytest.param(
            DaemonSetInfo(
                name="oh-lord",
                namespace=NamespaceName("have-mercy"),
                labels={},
                annotations=FilteredAnnotations({}),
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=Timestamp(1600000000.0),
                containers=ThinContainers(
                    images=frozenset({"i/name:0.5"}), names=[ContainerName("name")]
                ),
                cluster="cluster",
                kubernetes_cluster_hostname="host",
            ),
            UpdateStrategy(
                strategy=RollingUpdate(
                    max_surge="0",
                    max_unavailable="1",
                )
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "DaemonSet",
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "daemonset"],
                    inventory_attributes={
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
    section_strategy: UpdateStrategy,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventory_kube_daemonset(section_info, section_strategy)
    ) == sort_inventory_result(expected_inventory_result)


def test_inventory_kube_daemonset_calls_labels_to_table(
    mocker: MockerFixture,
) -> None:
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class DaemonSetInfoFactory(ModelFactory):
        __model__ = DaemonSetInfo
        selector = Selector(match_labels={}, match_expressions=[])

    section_info = DaemonSetInfoFactory.build()

    section_strategy = UpdateStrategy(strategy=OnDelete())

    mock = mocker.patch(
        "cmk.plugins.collection.agent_based.inventory_kube_daemonset.labels_to_table"
    )
    list(inventory_kube_daemonset(section_info, section_strategy))
    mock.assert_called_once()
