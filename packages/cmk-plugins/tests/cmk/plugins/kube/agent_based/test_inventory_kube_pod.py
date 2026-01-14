#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import Attributes, TableRow
from cmk.plugins.kube.agent_based.inventory_kube_pod import (
    _containers_to_table,
    inventorize_kube_pod,
)
from cmk.plugins.kube.schemata.api import (
    ContainerName,
    ContainerRunningState,
    ContainerStateType,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    IpAddress,
    NamespaceName,
    NodeName,
    PodUID,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import (
    ContainerSpec,
    ContainerSpecs,
    FilteredAnnotations,
    PodContainers,
    PodInfo,
)


@pytest.mark.parametrize(
    "section_info, section_containers, section_init_containers, section_container_specs, section_init_container_specs, expected_check_result",
    [
        pytest.param(
            PodInfo(
                namespace=NamespaceName("default"),
                name="name",
                creation_timestamp=Timestamp(1600000000.0),
                labels={},
                annotations=FilteredAnnotations({}),
                node=NodeName("minikube"),
                host_network=None,
                dns_policy="ClusterFirst",
                host_ip=IpAddress("192.168.49.2"),
                pod_ip=IpAddress("172.17.0.5"),
                qos_class="besteffort",
                restart_policy="Never",
                uid=PodUID("3336928e-b9e1-4774-a5c4-bf45b8f9f24e"),
                controllers=[],
                cluster="cluster",
                kubernetes_cluster_hostname="host",
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
                            type=ContainerStateType.waiting,
                            reason="PodInitializing",
                            detail=None,
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
                            type=ContainerStateType.terminated,
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
                    ContainerName("busybox"): ContainerSpec(image_pull_policy="Always"),
                }
            ),
            ContainerSpecs(
                containers={
                    ContainerName("busybox-init"): ContainerSpec(image_pull_policy="Always"),
                }
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "Pod",
                        "name": "name",
                        "namespace": "default",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "pod"],
                    inventory_attributes={
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
def test_inventorize_kube_pod(
    section_info: PodInfo,
    section_containers: PodContainers | None,
    section_init_containers: PodContainers | None,
    section_container_specs: ContainerSpecs,
    section_init_container_specs: ContainerSpecs,
    expected_check_result: Sequence[TableRow | Attributes],
) -> None:
    assert expected_check_result == list(
        inventorize_kube_pod(
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
                containers={ContainerName("busybox"): ContainerSpec(image_pull_policy="Always")}
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
                containers={ContainerName("busybox"): ContainerSpec(image_pull_policy="Always")}
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
                            type=ContainerStateType.waiting,
                            reason="PodInitializing",
                            detail=None,
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
                containers={ContainerName("busybox"): ContainerSpec(image_pull_policy="Always")}
            ),
            PodContainers(
                containers={
                    "busybox": ContainerStatus(
                        container_id="docker://1918700128d2badeaa720a2361546f9ad5ce35fb29d2fe5f96fb68b7f8e79d80",
                        image_id="docker-pullable://busybox@sha256:afcc7f1ac1b49db317a7196c902e61c6c3c4607d63599ee1a82d702d249a0ccb",
                        name="busybox",
                        image="busybox:latest",
                        ready=True,
                        state=ContainerRunningState(
                            type=ContainerStateType.running, start_time=1644140827
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
    container_statuses: PodContainers | None,
    expected_check_result: Sequence[TableRow | Attributes],
) -> None:
    assert expected_check_result == list(
        _containers_to_table(
            container_specs,
            container_statuses,
        )
    )


def test_inventorize_kube_pod_calls_labels_to_table(mocker: MockerFixture) -> None:
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class PodInfoFactory(ModelFactory):
        __model__ = PodInfo

    section_info = PodInfoFactory.build()

    class ContainerSpecsFactory(ModelFactory):
        __model__ = ContainerSpecs

    section_init_specs = ContainerSpecsFactory.build()
    section_specs = ContainerSpecsFactory.build()

    mock = mocker.patch("cmk.plugins.kube.agent_based.inventory_kube_pod.labels_to_table")
    list(inventorize_kube_pod(section_info, None, None, section_init_specs, section_specs))
    mock.assert_called_once()
