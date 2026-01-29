#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.base.legacy_checks.cadvisor_memory import (
    check_cadvisor_memory,
    discover_cadvisor_memory,
    parse_cadvisor_memory,
)


@pytest.fixture
def parsed() -> Mapping[str, float]:
    """Create parsed cAdvisor memory data using actual parse function."""
    string_table = [
        [
            '{"memory_usage_container": [{"value": "16162816", "labels": {"container": "coredns", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "pod": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_rss": [{"value": "9023488", "labels": {"__name__": "container_memory_rss", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_swap": [{"value": "0", "labels": {"__name__": "container_memory_swap", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_cache": [{"value": "6307840", "labels": {"__name__": "container_memory_cache", "beta_kubernetes_io_arch": "amd64", "beta_kubernetes_io_os": "linux", "container": "coredns", "container_name": "coredns", "id": "/kubepods/burstable/pod736910b3-0b55-4c11-8291-f9db987489e3/9cf6821b198e369693d5471644e45a620a33f7889b8bd8b2808e23a133312c50", "image": "sha256:eb516548c180f8a6e0235034ccee2428027896af16a509786da13022fe95fe8c", "instance": "minikube", "job": "kubernetes-cadvisor", "kubernetes_io_arch": "amd64", "kubernetes_io_hostname": "minikube", "kubernetes_io_os": "linux", "name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5", "namespace": "kube-system", "node_role_kubernetes_io_master": "", "pod": "coredns-5c98db65d4-b47gr", "pod_name": "coredns-5c98db65d4-b47gr"}, "host_selection_label": "name"}], "memory_usage_pod": [{"value": "17682432", "labels": {"pod": "coredns-5c98db65d4-b47gr"}}]}'
        ]
    ]
    return parse_cadvisor_memory(string_table)


def test_cadvisor_memory_discovery(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor memory discovery function."""
    result = list(discover_cadvisor_memory(parsed))

    # Should discover exactly one service
    assert len(result) == 1
    assert result[0] == (None, {})


def test_cadvisor_memory_check_container(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor memory check function for container memory."""
    result = list(check_cadvisor_memory(None, {}, parsed))

    # Should have exactly 4 results (usage, rss, cache, swap)
    assert len(result) == 4

    # Check usage result (container vs pod memory)
    state, summary, metrics = result[0]
    assert state == 0
    assert "Usage: 91.41%" in summary
    assert "15.4 MiB of 16.9 MiB" in summary
    assert "(Parent pod memory usage)" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "mem_used"
    assert metrics[0][1] == 16162816.0  # memory_usage_container
    assert metrics[0][5] == 17682432.0  # memory_usage_pod (total)

    # Check RSS result
    state, summary, metrics = result[1]
    assert state == 0
    assert "Resident size: 8812.0 kB" in summary
    assert len(metrics) == 0  # No metrics for RSS

    # Check cache result
    state, summary, metrics = result[2]
    assert state == 0
    assert "Cache: 6160.0 kB" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "mem_lnx_cached"
    assert metrics[0][1] == 6307840.0

    # Check swap result
    state, summary, metrics = result[3]
    assert state == 0
    assert "Swap: 0.0 kB" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "swap_used"
    assert metrics[0][1] == 0.0


def test_cadvisor_memory_check_pod_with_limit(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor memory check function for pod with memory limit."""
    # Modify parsed data to simulate pod-level check with memory limit
    pod_parsed = dict(parsed)
    del pod_parsed["memory_usage_container"]  # Remove container usage
    pod_parsed["memory_limit"] = 33554432.0  # Add 32MB limit

    result = list(check_cadvisor_memory(None, {}, pod_parsed))

    # Should have exactly 4 results
    assert len(result) == 4

    # Check usage result (pod vs limit)
    state, summary, metrics = result[0]
    assert state == 0
    assert "Usage:" in summary
    # Should not have "(Parent pod memory usage)" suffix
    assert "(Parent pod memory usage)" not in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "mem_used"
    assert metrics[0][1] == 17682432.0  # memory_usage_pod
    assert metrics[0][5] == 33554432.0  # memory_limit (total)


def test_cadvisor_memory_check_pod_with_machine_memory(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor memory check function for pod against machine memory."""
    # Modify parsed data to simulate pod-level check with machine memory
    pod_parsed = dict(parsed)
    del pod_parsed["memory_usage_container"]  # Remove container usage
    pod_parsed["memory_machine"] = 8589934592.0  # Add 8GB machine memory

    result = list(check_cadvisor_memory(None, {}, pod_parsed))

    # Should have exactly 4 results
    assert len(result) == 4

    # Check usage result (pod vs machine memory)
    state, summary, metrics = result[0]
    assert state == 0
    assert "Usage:" in summary
    assert "(Available Machine Memory)" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "mem_used"
    assert metrics[0][1] == 17682432.0  # memory_usage_pod
    assert metrics[0][5] == 8589934592.0  # memory_machine (total)


def test_cadvisor_memory_discovery_empty_section() -> None:
    """Test cAdvisor memory discovery function with empty section."""
    result = list(discover_cadvisor_memory({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_cadvisor_memory_parse_function() -> None:
    """Test cAdvisor memory parse function with the exact dataset."""
    string_table = [
        [
            '{"memory_usage_container": [{"value": "16162816", "labels": {}}], "memory_rss": [{"value": "9023488", "labels": {}}], "memory_swap": [{"value": "0", "labels": {}}], "memory_cache": [{"value": "6307840", "labels": {}}], "memory_usage_pod": [{"value": "17682432", "labels": {}}]}'
        ]
    ]

    result = parse_cadvisor_memory(string_table)

    # Verify parsed structure
    expected_keys = {
        "memory_usage_container",
        "memory_rss",
        "memory_swap",
        "memory_cache",
        "memory_usage_pod",
    }
    assert set(result.keys()) == expected_keys

    # Check parsed values
    assert result["memory_usage_container"] == 16162816.0
    assert result["memory_rss"] == 9023488.0
    assert result["memory_swap"] == 0.0
    assert result["memory_cache"] == 6307840.0
    assert result["memory_usage_pod"] == 17682432.0


def test_cadvisor_memory_parse_multiple_entries() -> None:
    """Test cAdvisor memory parse function skips entries with multiple values."""
    string_table = [
        [
            '{"memory_usage_container": [{"value": "16162816"}, {"value": "20000000"}], "memory_rss": [{"value": "9023488"}]}'
        ]
    ]

    result = parse_cadvisor_memory(string_table)

    # Should only include memory_rss (single entry), not memory_usage_container (multiple entries)
    assert "memory_rss" in result
    assert "memory_usage_container" not in result
    assert result["memory_rss"] == 9023488.0


def test_cadvisor_memory_parse_invalid_value() -> None:
    """Test cAdvisor memory parse function handles missing or invalid values."""
    string_table = [
        [
            '{"memory_usage_container": [{"no_value": "16162816"}], "memory_rss": [{"value": "9023488"}]}'
        ]
    ]

    result = parse_cadvisor_memory(string_table)

    # Should only include memory_rss (valid), not memory_usage_container (missing "value" key)
    assert "memory_rss" in result
    assert "memory_usage_container" not in result
    assert result["memory_rss"] == 9023488.0
