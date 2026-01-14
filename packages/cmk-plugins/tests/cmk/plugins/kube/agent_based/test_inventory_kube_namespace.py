#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.kube.agent_based.inventory_kube_namespace import (
    inventorize_kube_namespace,
)
from cmk.plugins.kube.schemata.api import NamespaceName
from cmk.plugins.kube.schemata.section import FilteredAnnotations, NamespaceInfo
from tests.cmk.plugins.kube.agent_based.utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, expected_inventory_result",
    [
        pytest.param(
            NamespaceInfo(
                name=NamespaceName("Liam"),  # first result when googling: 'best names'
                labels={},
                annotations=FilteredAnnotations({}),
                creation_timestamp=None,
                cluster="a",
                kubernetes_cluster_hostname="host",
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "Namespace",
                        "name": "Liam",
                        "namespace": "Liam",
                    },
                ),
            ],
            id="overall look of Namespace inventory",
        ),
    ],
)
def test_inventorize_kube_namespace(
    section_info: NamespaceInfo,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(inventorize_kube_namespace(section_info)) == sort_inventory_result(
        expected_inventory_result
    )
