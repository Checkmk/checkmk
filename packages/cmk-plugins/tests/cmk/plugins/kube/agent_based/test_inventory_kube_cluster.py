#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.kube.agent_based.inventory_kube_cluster import inventory_kube_cluster
from cmk.plugins.kube.schemata.api import GitVersion
from cmk.plugins.kube.schemata.section import ClusterInfo
from tests.cmk.plugins.kube.agent_based.utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, expected_inventory_result",
    [
        pytest.param(
            ClusterInfo(
                name="Liam",  # first result when googling: 'best names'
                version=GitVersion("v1.22.2"),
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "cluster",
                        "name": "Liam",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "cluster"],
                    inventory_attributes={
                        "version": "v1.22.2",
                    },
                    status_attributes={},
                ),
            ],
            id="overall look of Cluster inventory",
        ),
    ],
)
def test_inventorize_kube_statefulset(
    section_info: ClusterInfo,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(inventory_kube_cluster(section_info)) == sort_inventory_result(
        expected_inventory_result
    )
