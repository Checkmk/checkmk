#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.kube.agent_based.inventory_kube_deployment import (
    inventorize_kube_deployment,
)
from cmk.plugins.kube.schemata.api import (
    ContainerName,
    NamespaceName,
    Recreate,
    RollingUpdate,
    Selector,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import (
    DeploymentInfo,
    FilteredAnnotations,
    ThinContainers,
    UpdateStrategy,
)
from tests.cmk.plugins.kube.agent_based.utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_strategy, expected_check_result",
    [
        pytest.param(
            DeploymentInfo(
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
                    max_surge="25%",
                    max_unavailable="25%",
                )
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "Deployment",
                        "name": "oh-lord",
                        "namespace": "have-mercy",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "deployment"],
                    inventory_attributes={
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
def test_inventorize_kube_deployment(
    section_info: DeploymentInfo,
    section_strategy: UpdateStrategy,
    expected_check_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(
        inventorize_kube_deployment(section_info, section_strategy)
    ) == sort_inventory_result(expected_check_result)


def test_inventorize_kube_deployment_calls_labels_to_table(
    mocker: MockerFixture,
) -> None:
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class DeploymentInfoFactory(ModelFactory):
        __model__ = DeploymentInfo
        selector = Selector(match_labels={}, match_expressions=[])

    section_info = DeploymentInfoFactory.build()

    section_strategy = UpdateStrategy(strategy=Recreate())

    mock = mocker.patch("cmk.plugins.kube.agent_based.inventory_kube_deployment.labels_to_table")
    list(inventorize_kube_deployment(section_info, section_strategy))
    mock.assert_called_once()
