#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_k8s_job_container import inventory_k8s_job_container

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        ({}, []),
        (
            {
                "Name": {
                    "image": "Image",
                    "image_pull_policy": "Image pull policy",
                },
            },
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "job_container"],
                    key_columns={
                        "name": "Name",
                    },
                    inventory_columns={
                        "image": "Image",
                        "image_pull_policy": "Image pull policy",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_k8s_job_container(parsed, expected_result):
    assert sort_inventory_result(inventory_k8s_job_container(parsed)) == sort_inventory_result(
        expected_result
    )
