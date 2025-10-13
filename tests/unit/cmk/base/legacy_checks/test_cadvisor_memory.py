#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.cadvisor_memory import (
    check_cadvisor_memory,
    discover_cadvisor_memory,
    parse_cadvisor_memory,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"memory_usage_container": [{"value": "16162816", "labels": {"container": "coredns", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "pod": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_rss": [{"value": "9023488", "labels": {"__name__": "container_memory_rss", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_swap": [{"value": "0", "labels": {"__name__": "container_memory_swap", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_cache": [{"value": "6307840", "labels": {"__name__": "container_memory_cache", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_usage_pod": [{"value": "17682432", "labels": {"pod": "coredns-5c98db65d4-b47gr"}}]}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_cadvisor_memory(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for cadvisor_memory check."""
    parsed = parse_cadvisor_memory(string_table)
    result = list(discover_cadvisor_memory(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{"memory_usage_container": [{"value": "16162816", "labels": {"container": "coredns", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "pod": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_rss": [{"value": "9023488", "labels": {"__name__": "container_memory_rss", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_swap": [{"value": "0", "labels": {"__name__": "container_memory_swap", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_cache": [{"value": "6307840", "labels": {"__name__": "container_memory_cache", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_usage_pod": [{"value": "17682432", "labels": {"pod": "coredns-5c98db65d4-b47gr"}}]}'
                ]
            ],
            [
                (
                    0,
                    "Usage: 91.41% - 15.4 MiB of 16.9 MiB (Parent pod memory usage)",
                    [("mem_used", 16162816.0, None, None, 0, 17682432.0)],
                ),
                (0, "Resident size: 8812.0 kB", []),
                (0, "Cache: 6160.0 kB", [("mem_lnx_cached", 6307840.0, None, None)]),
                (0, "Swap: 0.0 kB", [("swap_used", 0.0, None, None)]),
            ],
        ),
    ],
)
def test_check_cadvisor_memory(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for cadvisor_memory check."""
    parsed = parse_cadvisor_memory(string_table)
    result = list(check_cadvisor_memory(item, params, parsed))
    assert result == expected_results
