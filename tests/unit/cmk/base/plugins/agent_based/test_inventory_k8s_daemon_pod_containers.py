#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_k8s_daemon_pod_containers import (
    inventory_k8s_daemon_pod_containers,
    parse_k8s_daemon_pod_containers,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        ([], []),
        (
            [
                [
                    '{"name2": {"image": "Image 2", "image_pull_policy": "Image Pull Policy 2"}, "name1": {"image": "Image 1", "image_pull_policy": "Image Pull Policy 1"}}'
                ]
            ],
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "daemon_pod_containers"],
                    key_columns={
                        "name": "name1",
                    },
                    inventory_columns={
                        "image": "Image 1",
                        "image_pull_policy": "Image Pull Policy 1",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "daemon_pod_containers"],
                    key_columns={
                        "name": "name2",
                    },
                    inventory_columns={
                        "image": "Image 2",
                        "image_pull_policy": "Image Pull Policy 2",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_k8s_daemon_pod_containers(raw_section, expected_result) -> None:
    assert sort_inventory_result(
        inventory_k8s_daemon_pod_containers(parse_k8s_daemon_pod_containers(raw_section))
    ) == sort_inventory_result(expected_result)
