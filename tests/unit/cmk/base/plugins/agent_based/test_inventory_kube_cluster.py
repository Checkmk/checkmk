#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_cluster import inventory_kube_cluster
from cmk.base.plugins.agent_based.utils.kube import ClusterInfo

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, expected_inventory_result",
    [
        pytest.param(
            ClusterInfo(
                name="Liam",  # first result when googling: 'best names'
                version="v1.22.2",
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
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
def test_inventory_kube_statefulset(
    section_info: ClusterInfo,
    expected_inventory_result: Sequence[Any],
) -> None:
    assert sort_inventory_result(inventory_kube_cluster(section_info)) == sort_inventory_result(
        expected_inventory_result
    )
