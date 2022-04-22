#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_kube_node import inventory_kube_node
from cmk.base.plugins.agent_based.utils.kube import HealthZ, KubeletInfo, NodeAddress, NodeInfo

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "section_info, section_kubelet, expected_check_result",
    [
        pytest.param(
            NodeInfo(
                architecture="amd64",
                kernel_version="5.13.0-27-generic",
                os_image="Ubuntu 20.04.2 LTS",
                operating_system="linux",
                container_runtime_version="docker://20.10.8",
                name="minikube",
                creation_timestamp=1640000000.0,
                labels={},
                annotations={},
                addresses=[
                    NodeAddress(type_="Hostname", address="k8-21"),
                    NodeAddress(type_="ExternalIP", address="10.200.3.21"),
                ],
                cluster="cluster",
            ),
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=HealthZ(status_code=200, response="ok", verbose_response=None),
            ),
            [
                Attributes(
                    path=["software", "applications", "kube", "metadata"],
                    inventory_attributes={
                        "object": "Node",
                        "name": "minikube",
                    },
                ),
                Attributes(
                    path=["software", "applications", "kube", "node"],
                    inventory_attributes={
                        "operating_system": "linux",
                        "os_image": "Ubuntu 20.04.2 LTS",
                        "kernel_version": "5.13.0-27-generic",
                        "architecture": "amd64",
                        "container_runtime_version": "docker://20.10.8",
                        "kubelet_version": "1.2.3",
                        "kube_proxy_version": "1.2.3",
                    },
                    status_attributes={},
                ),
                TableRow(
                    path=["software", "applications", "kube", "network"],
                    key_columns={"ip": "k8-21"},
                    inventory_columns={"address_type": "Hostname"},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kube", "network"],
                    key_columns={"ip": "10.200.3.21"},
                    inventory_columns={"address_type": "ExternalIP"},
                    status_columns={},
                ),
            ],
            id="overall look of node inventory",
        ),
    ],
)
def test_inventory_kube_node(
    section_info: NodeInfo,
    section_kubelet: KubeletInfo,
    expected_check_result: Sequence[Union[TableRow, Attributes]],
) -> None:
    assert sort_inventory_result(
        inventory_kube_node(section_info, section_kubelet)
    ) == sort_inventory_result(expected_check_result)


def test_inventory_kube_node_calls_labels_to_table(mocker):
    """Test coverage and uniform look across inventories relies on the inventories calling
    labels_to_table."""

    class NodeInfoFactory(ModelFactory):
        __model__ = NodeInfo

    section_info = NodeInfoFactory.build()

    class KubeletInfoFactory(ModelFactory):
        __model__ = KubeletInfo

    section_kubelet = KubeletInfoFactory.build()

    mock = mocker.patch("cmk.base.plugins.agent_based.inventory_kube_node.labels_to_table")
    list(inventory_kube_node(section_info, section_kubelet))
    mock.assert_called_once()
