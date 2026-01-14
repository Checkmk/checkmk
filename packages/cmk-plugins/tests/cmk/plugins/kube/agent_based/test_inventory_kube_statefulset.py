#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Sequence
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import Attributes
from cmk.plugins.kube.agent_based.inventory_kube_statefulset import (
    inventorize_kube_statefulset,
)
from cmk.plugins.kube.schemata.api import (
    ContainerName,
    NamespaceName,
    Recreate,
    Selector,
    StatefulSetRollingUpdate,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import (
    FilteredAnnotations,
    StatefulSetInfo,
    ThinContainers,
    UpdateStrategy,
)
from tests.cmk.plugins.kube.agent_based.utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_inventory_result",
    [
        pytest.param(
            StatefulSetInfo(
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
def test_inventorize_kube_statefulset(
    section_info: StatefulSetInfo,
    section_strategy: UpdateStrategy,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventorize_kube_statefulset(section_info, section_strategy)
    ) == sort_inventory_result(expected_inventory_result)


def test_inventorize_kube_statefulset_calls_labels_to_table(
    mocker: MockerFixture,
) -> None:
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class StatefulSetInfoFactory(ModelFactory):
        __model__ = StatefulSetInfo
        selector = Selector(match_labels={}, match_expressions=[])

    section_info = StatefulSetInfoFactory.build()

    section_strategy = UpdateStrategy(strategy=Recreate())

    mock = mocker.patch("cmk.plugins.kube.agent_based.inventory_kube_statefulset.labels_to_table")
    list(inventorize_kube_statefulset(section_info, section_strategy))
    mock.assert_called_once()
