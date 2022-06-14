#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State, TableRow
from cmk.base.plugins.agent_based.k8s_roles import inventory_k8s_roles
from cmk.base.plugins.agent_based.utils.k8s import parse_json

from .utils_inventory import sort_inventory_result

_AGENT_OUTPUT = [
    [
        '{"roles": [{"creation_timestamp": 1538034890.0, "namespace": "kube-public", "name": "kubeadm:bootstrap-signer-clusterinfo"}, {"creation_timestamp": 1538034889.0, "namespace": "kube-public", "name": "system:controller:bootstrap-signer"}, {"creation_timestamp": 1538034888.0, "namespace": "kube-system", "name": "extension-apiserver-authentication-reader"}, {"creation_timestamp": 1538034889.0, "namespace": "kube-system", "name": "system::leader-locking-kube-controller-manager"}, {"creation_timestamp": 1538034889.0, "namespace": "kube-system", "name": "system::leader-locking-kube-scheduler"}, {"creation_timestamp": 1538034888.0, "namespace": "kube-system", "name": "system:controller:bootstrap-signer"}, {"creation_timestamp": 1538034889.0, "namespace": "kube-system", "name": "system:controller:cloud-provider"}, {"creation_timestamp": 1538034889.0, "namespace": "kube-system", "name": "system:controller:token-cleaner"}], "cluster_roles": [{"creation_timestamp": 1538034887.0, "namespace": null, "name": "admin"}, {"creation_timestamp": 1539699586.0, "namespace": null, "name": "check-mk"}, {"creation_timestamp": 1538034883.0, "namespace": null, "name": "cluster-admin"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "edit"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:aggregate-to-admin"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:aggregate-to-edit"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:aggregate-to-view"}, {"creation_timestamp": 1544712904.0, "namespace": null, "name": "system:aggregated-metrics-reader"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:auth-delegator"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:aws-cloud-provider"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:basic-user"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:certificates.k8s.io:certificatesigningrequests:nodeclient"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:certificates.k8s.io:certificatesigningrequests:selfnodeclient"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:attachdetach-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:certificate-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:clusterrole-aggregation-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:cronjob-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:daemon-set-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:deployment-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:disruption-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:endpoint-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:generic-garbage-collector"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:horizontal-pod-autoscaler"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:job-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:namespace-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:node-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:persistent-volume-binder"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:pod-garbage-collector"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:pv-protection-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:pvc-protection-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:replicaset-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:replication-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:resourcequota-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:route-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:service-account-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:service-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:statefulset-controller"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:controller:ttl-controller"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:discovery"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:heapster"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:kube-aggregator"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:kube-controller-manager"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:kube-dns"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:kube-scheduler"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:kubelet-api-admin"}, {"creation_timestamp": 1544712904.0, "namespace": null, "name": "system:metrics-server"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:node"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:node-bootstrapper"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:node-problem-detector"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:node-proxier"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "system:persistent-volume-provisioner"}, {"creation_timestamp": 1538034888.0, "namespace": null, "name": "system:volume-scheduler"}, {"creation_timestamp": 1538034887.0, "namespace": null, "name": "view"}]}'
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (_AGENT_OUTPUT, [Service()]),
    ],
)
def test_discover_k8s_roles(fix_register, string_table, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("k8s_roles")]
    section = parse_json(string_table)
    assert sorted(check_plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Result(state=State.OK, summary="Total: 61"),
                Metric("k8s_total_roles", 61.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Cluster roles: 53"),
                Metric("k8s_cluster_roles", 53.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Roles: 8"),
                Metric("k8s_roles", 8.0, boundaries=(0.0, None)),
            ],
        ),
    ],
)
def test_check_k8s_roles(fix_register, string_table, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("k8s_roles")]
    section = parse_json(string_table)
    assert list(check_plugin.check_function(params={}, section=section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            {
                "roles": [],
                "cluster_roles": [],
            },
            [],
        ),
        (
            {
                "roles": [
                    {"creation_timestamp": 1, "namespace": "public", "name": "name1"},
                    {"creation_timestamp": 2, "namespace": "public", "name": "name2"},
                ],
                "cluster_roles": [
                    {"creation_timestamp": 3, "namespace": "system", "name": "cluster-name3"},
                    {"creation_timestamp": 4, "namespace": None, "name": "cluster-name4"},
                ],
            },
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "roles"],
                    key_columns={
                        "role": "cluster-name3",
                    },
                    inventory_columns={
                        "namespace": "system",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "roles"],
                    key_columns={
                        "role": "cluster-name4",
                    },
                    inventory_columns={
                        "namespace": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "roles"],
                    key_columns={
                        "role": "name1",
                    },
                    inventory_columns={
                        "namespace": "public",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "roles"],
                    key_columns={
                        "role": "name2",
                    },
                    inventory_columns={
                        "namespace": "public",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_k8s_roles(section, expected_result) -> None:
    assert sort_inventory_result(inventory_k8s_roles(section)) == sort_inventory_result(
        expected_result
    )
