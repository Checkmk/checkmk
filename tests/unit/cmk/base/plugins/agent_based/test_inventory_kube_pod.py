#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence, Union

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_kube_pod import _containers_to_table, inventory_kube_pod
from cmk.base.plugins.agent_based.utils.kube import (
    ContainerRunningState,
    ContainerSpec,
    ContainerSpecs,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
    PodInfo,
)


@pytest.mark.parametrize(
    "section_info, section_containers, section_init_containers, section_container_specs, section_init_container_specs, expected_check_result",
    [
        pytest.param(
            PodInfo(
                namespace="default",
                name="name",
                creation_timestamp=1600000000.0,
                labels={},
                node="minikube",
                host_network=None,
                dns_policy="ClusterFirst",
                host_ip="192.168.49.2",
                pod_ip="172.17.0.5",
                qos_class="besteffort",
                restart_policy="Never",
                uid="3336928e-b9e1-4774-a5c4-bf45b8f9f24e",
                controllers=[],
                cluster="cluster",
            ),
            PodContainers(
                containers={
                    "busybox": ContainerStatus(
                        container_id=None,
                        image_id="",
                        name="busybox",
                        image="busybox",
                        ready=False,
                        state=ContainerWaitingState(
                            type="waiting", reason="PodInitializing", detail=None
                        ),
                        restart_count=0,
                    )
                }
            ),
            PodContainers(
                containers={
                    "busybox-init": ContainerStatus(
                        container_id="some-id",
                        image_id="somde-id",
                        name="busybox-init",
                        image="busybox:latest",
                        ready=False,
                        state=ContainerTerminatedState(
                            type="terminated",
                            exit_code=1,
                            start_time=1644141019,
                            end_time=1644141019,
                            reason="Error",
                            detail=None,
                        ),
                        restart_count=5,
                    )
                }
            ),
            ContainerSpecs(
                containers={
                    "busybox": ContainerSpec(name="busybox", image_pull_policy="Always"),
                }
            ),
            ContainerSpecs(
                containers={
                    "busybox-init": ContainerSpec(name="busybox-init", image_pull_policy="Always"),
                }
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "pod"],
                    inventory_attributes={
                        "name": "name",
                        "namespace": "default",
                        "dns_policy": "ClusterFirst",
                        "host_ip": "192.168.49.2",
                        "host_network": None,
                        "node": "minikube",
                        "pod_ip": "172.17.0.5",
                        "qos_class": "besteffort",
                    },
                    status_attributes={},
                ),
                TableRow(
                    path=["software", "applications", "kube", "containers"],
                    key_columns={"name": "busybox"},
                    inventory_columns={
                        "image_pull_policy": "Always",
                        "ready": "no",
                        "restart_count": 0,
                        "image": "busybox",
                        "image_id": "",
                        "container_id": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kube", "containers"],
                    key_columns={"name": "busybox-init"},
                    inventory_columns={
                        "image_pull_policy": "Always",
                        "ready": "no",
                        "restart_count": 5,
                        "image": "busybox:latest",
                        "image_id": "somde-id",
                        "container_id": "some-id",
                    },
                    status_columns={},
                ),
            ],
            id="overall look of pod inventory",
        ),
    ],
)
def test_inventory_kube_pod(
    section_info: PodInfo,
    section_containers: Optional[PodContainers],
    section_init_containers: Optional[PodContainers],
    section_container_specs: ContainerSpecs,
    section_init_container_specs: ContainerSpecs,
    expected_check_result: Sequence[Union[TableRow, Attributes]],
) -> None:

    assert expected_check_result == list(
        inventory_kube_pod(
            section_info,
            section_containers,
            section_init_containers,
            section_container_specs,
            section_init_container_specs,
        )
    )


@pytest.mark.parametrize(
    "container_specs, container_statuses, expected_check_result",
    [
        pytest.param(
            ContainerSpecs(containers={}),
            None,
            [],
            id="no init containers specified",
        ),
        pytest.param(
            ContainerSpecs(
                containers={"busybox": ContainerSpec(name="busybox", image_pull_policy="Always")}
            ),
            None,
            [
                TableRow(
                    path=["software", "applications", "kube", "containers"],
                    key_columns={"name": "busybox"},
                    inventory_columns={"image_pull_policy": "Always", "ready": "no"},
                    status_columns={},
                )
            ],
            id="no status information, since pod is not scheduled",
        ),
        pytest.param(
            ContainerSpecs(
                containers={"busybox": ContainerSpec(name="busybox", image_pull_policy="Always")}
            ),
            PodContainers(
                containers={
                    "busybox": ContainerStatus(
                        container_id=None,
                        image_id="",
                        name="busybox",
                        image="busybox",
                        ready=False,
                        state=ContainerWaitingState(
                            type="waiting", reason="PodInitializing", detail=None
                        ),
                        restart_count=0,
                    )
                }
            ),
            [
                TableRow(
                    path=["software", "applications", "kube", "containers"],
                    key_columns={"name": "busybox"},
                    inventory_columns={
                        "image_pull_policy": "Always",
                        "ready": "no",
                        "restart_count": 0,
                        "image": "busybox",
                        "image_id": "",
                        "container_id": None,
                    },
                    status_columns={},
                )
            ],
            id="reduced status information for regular containers, since init containers are still running",
        ),
        pytest.param(
            ContainerSpecs(
                containers={"busybox": ContainerSpec(name="busybox", image_pull_policy="Always")}
            ),
            PodContainers(
                containers={
                    "busybox": ContainerStatus(
                        container_id="docker://1918700128d2badeaa720a2361546f9ad5ce35fb29d2fe5f96fb68b7f8e79d80",
                        image_id="docker-pullable://busybox@sha256:afcc7f1ac1b49db317a7196c902e61c6c3c4607d63599ee1a82d702d249a0ccb",
                        name="busybox",
                        image="busybox:latest",
                        ready=True,
                        state=ContainerRunningState(type="running", start_time=1644140827),
                        restart_count=0,
                    )
                }
            ),
            [
                TableRow(
                    path=["software", "applications", "kube", "containers"],
                    key_columns={"name": "busybox"},
                    inventory_columns={
                        "image_pull_policy": "Always",
                        "ready": "yes",
                        "restart_count": 0,
                        "image": "busybox:latest",
                        "image_id": "docker-pullable://busybox@sha256:afcc7f1ac1b49db317a7196c902e61c6c3c4607d63599ee1a82d702d249a0ccb",
                        "container_id": "docker://1918700128d2badeaa720a2361546f9ad5ce35fb29d2fe5f96fb68b7f8e79d80",
                    },
                    status_columns={},
                )
            ],
            id="regular container after all init containers succedded",
        ),
    ],
)
def test_container_to_table(
    container_specs: ContainerSpecs,
    container_statuses: Optional[PodContainers],
    expected_check_result: Sequence[Union[TableRow, Attributes]],
) -> None:

    assert expected_check_result == list(
        _containers_to_table(
            container_specs,
            container_statuses,
        )
    )
