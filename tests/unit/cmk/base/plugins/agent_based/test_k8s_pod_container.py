#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State, TableRow
from cmk.base.plugins.agent_based.k8s_pod_container import inventory_k8s_pod_container

from .utils_inventory import sort_inventory_result

_SECTION = {
    "pi": {
        "image_pull_policy": "Always",
        "state_reason": "Completed",
        "image": "perl",
        "container_id": "94d698838e88b72fdaf7b48dd7c227f5d36915c3279af6b1da33d397cef0c276",
        "restart_count": 0,
        "image_id": "docker-pullable://perl@sha256:5cada8a3709c245b0256a4d986801e598abf95576eb01767bde94d567e23104e",
        "state": "terminated",
        "ready": False,
        "state_exit_code": 0,
    }
}


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (_SECTION, [Service()]),
    ],
)
def test_discover_k8s_pod_container(fix_register, section, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("k8s_pod_container")]
    assert sorted(check_plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            _SECTION,
            [
                Result(state=State.OK, summary="Ready: 0/1"),
                Metric("docker_all_containers", 1.0, boundaries=(0.0, 1.0)),
                Metric("ready_containers", 0.0, boundaries=(0.0, 1.0)),
                Result(state=State.OK, summary="Running: 0"),
                Result(state=State.OK, summary="Waiting: 0"),
                Result(state=State.OK, summary="Terminated: 1"),
            ],
        ),
    ],
)
def test_check_k8s_pod_container(fix_register, section, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("k8s_pod_container")]
    assert list(check_plugin.check_function(params={}, section=section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        ({}, []),
        (
            _SECTION,
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "pod_container"],
                    key_columns={
                        "name": "pi",
                    },
                    inventory_columns={
                        "image": "perl",
                        "image_pull_policy": "Always",
                        "image_id": "5cada8a3709c",
                    },
                    status_columns={
                        "ready": "no",
                        "restart_count": 0,
                        "container_id": "94d698838e88",
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_k8s_pod_container(section, expected_result) -> None:
    assert sort_inventory_result(inventory_k8s_pod_container(section)) == sort_inventory_result(
        expected_result
    )
