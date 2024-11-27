#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.kube.server_side_calls.special_agent import special_agent_kube
from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    IPv4Config,
    NoProxy,
    Secret,
    URLProxy,
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "https://11.211.3.32",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                    "timeout": {"connect": 5, "read": 8},
                },
                "usage_endpoint": (
                    "cluster_collector",
                    {
                        "endpoint_v2": "https://11.211.3.32:20026",
                        "verify_cert": False,
                        "timeout": {"connect": 10, "read": 12},
                    },
                ),
                "monitored_objects": ["pods"],
            },
            [
                "--cluster",
                "cluster",
                "--kubernetes-cluster-hostname",
                "host",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "https://11.211.3.32",
                "--api-server-proxy",
                "NO_PROXY",
                "--k8s-api-connect-timeout",
                "5",
                "--k8s-api-read-timeout",
                "8",
                "--cluster-collector-endpoint",
                "https://11.211.3.32:20026",
                "--usage-proxy",
                "FROM_ENVIRONMENT",
                "--usage-connect-timeout",
                "10",
                "--usage-read-timeout",
                "12",
            ],
        ),
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://11.211.3.32:8080",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                },
                "usage_endpoint": (
                    "cluster_collector",
                    {
                        "endpoint_v2": "https://11.211.3.32:20026",
                        "verify_cert": True,
                    },
                ),
                "monitored_objects": ["pods"],
            },
            [
                "--cluster",
                "cluster",
                "--kubernetes-cluster-hostname",
                "host",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "http://11.211.3.32:8080",
                "--api-server-proxy",
                "NO_PROXY",
                "--cluster-collector-endpoint",
                "https://11.211.3.32:20026",
                "--usage-proxy",
                "FROM_ENVIRONMENT",
                "--usage-verify-cert",
            ],
        ),
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://localhost:8080",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                },
                "usage_endpoint": (
                    "cluster_collector",
                    {
                        "endpoint_v2": "https://11.211.3.32:20026",
                        "verify_cert": False,
                    },
                ),
                "monitored_objects": ["pods", "namespaces"],
            },
            [
                "--cluster",
                "cluster",
                "--kubernetes-cluster-hostname",
                "host",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "namespaces",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "http://localhost:8080",
                "--api-server-proxy",
                "NO_PROXY",
                "--cluster-collector-endpoint",
                "https://11.211.3.32:20026",
                "--usage-proxy",
                "FROM_ENVIRONMENT",
            ],
        ),
    ],
)
def test_parse_arguments(params: Mapping[str, object], expected_args: Sequence[str]) -> None:
    """Tests if all required arguments are present."""
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args


def test_parse_arguments_with_no_cluster_endpoint() -> None:
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://127.0.0.1",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods"],
    }
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="127.0.0.1"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--api-server-endpoint",
        "https://127.0.0.1",
        "--api-server-proxy",
        "NO_PROXY",
    ]


def test_cronjob_pvcs_piggyback_option() -> None:
    """Test the cronjob and pvc piggyback option"""
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods", "cronjobs_pods", "pvcs"],
    }
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "cronjobs_pods",
        "pvcs",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]


def test_cluster_resource_aggregation() -> None:
    """Test the cluster-resource-aggregation option"""
    params: Mapping[str, object] = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods"],
        "cluster_resource_aggregation": (
            "cluster_aggregation_exclude_node_roles",
            ["control*", "worker"],
        ),
    }
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-exclude-node-roles",
        "control*",
        "worker",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods"],
        "cluster_resource_aggregation": ("cluster_aggregation_include_all_nodes", None),
    }
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-include-all-nodes",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods"],
    }
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]


def test_host_labels_annotation_selection() -> None:
    """Test the import_annotations option"""
    # Option not set -> no annotations imported. This special case is covered
    # by test_parse_arguments. If test_parse_arguments is migrated, this
    # special case needs to be reconsidered.

    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    # Explicit no filtering
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "import_annotations": ("include_annotations_as_host_labels", None),
        "monitored_objects": ["pods"],
    }
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--include-annotations-as-host-labels",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]

    # Explicit filtering
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "import_annotations": (
            "include_matching_annotations_as_host_labels",
            "checkmk-monitoring$",
        ),
        "monitored_objects": ["pods"],
    }
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--include-matching-annotations-as-host-labels",
        "checkmk-monitoring$",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]


def test_parse_namespace_patterns() -> None:
    params = {
        "cluster_name": "cluster",
        "token": Secret(1),
        "kubernetes_api_server": {
            "endpoint_v2": "https://11.211.3.32",
            "verify_cert": False,
            "proxy": NoProxy(),
        },
        "monitored_objects": ["pods"],
        "namespaces": ("namespace_include_patterns", ["default", "kube-system"]),
    }
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == [
        "--cluster",
        "cluster",
        "--kubernetes-cluster-hostname",
        "host",
        "--token",
        Secret(1).unsafe(),
        "--monitored-objects",
        "pods",
        "--namespace-include-patterns",
        "default",
        "--namespace-include-patterns",
        "kube-system",
        "--cluster-aggregation-exclude-node-roles",
        "control-plane",
        "infra",
        "--api-server-endpoint",
        "https://11.211.3.32",
        "--api-server-proxy",
        "NO_PROXY",
    ]


@pytest.mark.parametrize(
    "params, expected_arguments",
    [
        (
            {
                "cluster_name": "test",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "https://127.0.0.1",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                },
                "monitored_objects": ["pods"],
            },
            [
                "--cluster",
                "test",
                "--kubernetes-cluster-hostname",
                "kubi",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "https://127.0.0.1",
                "--api-server-proxy",
                "NO_PROXY",
            ],
        ),
        (
            {
                "cluster_name": "test",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://127.0.0.1:8080",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                },
                "monitored_objects": ["pods"],
            },
            [
                "--cluster",
                "test",
                "--kubernetes-cluster-hostname",
                "kubi",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "http://127.0.0.1:8080",
                "--api-server-proxy",
                "NO_PROXY",
            ],
        ),
        (
            {
                "cluster_name": "test",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://localhost:8080",
                    "verify_cert": True,
                    "proxy": NoProxy(),
                },
                "monitored_objects": ["pods"],
            },
            [
                "--cluster",
                "test",
                "--kubernetes-cluster-hostname",
                "kubi",
                "--token",
                Secret(1).unsafe(),
                "--monitored-objects",
                "pods",
                "--cluster-aggregation-exclude-node-roles",
                "control-plane",
                "infra",
                "--api-server-endpoint",
                "http://localhost:8080",
                "--api-server-proxy",
                "NO_PROXY",
                "--verify-cert-api",
            ],
        ),
    ],
)
def test_client_configuration_host(
    params: Mapping[str, object], expected_arguments: Sequence[str]
) -> None:
    host_config = HostConfig(name="kubi", ipv4_config=IPv4Config(address="127.0.0.1"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    assert commands[0].command_arguments == expected_arguments


@pytest.mark.parametrize(
    "params,expected_proxy_arg",
    [
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "https://11.211.3.32",
                    "verify_cert": False,
                    "proxy": NoProxy(),
                },
                "monitored_objects": ["pods"],
            },
            "NO_PROXY",
        ),
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://localhost:8001",
                    "verify_cert": False,
                },
                "monitored_objects": ["pods"],
            },
            "FROM_ENVIRONMENT",
        ),
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://localhost:8001",
                    "verify_cert": False,
                    "proxy": URLProxy(url="http://test:test@127.0.0.1:8080"),
                },
                "monitored_objects": ["pods"],
            },
            "http://test:test@127.0.0.1:8080",
        ),
        (
            {
                "cluster_name": "cluster",
                "token": Secret(1),
                "kubernetes_api_server": {
                    "endpoint_v2": "http://localhost:8001",
                    "verify_cert": False,
                    "proxy": EnvProxy(),
                },
                "monitored_objects": ["pods"],
            },
            "FROM_ENVIRONMENT",
        ),
    ],
)
def test_proxy_arguments(params: Mapping[str, object], expected_proxy_arg: str) -> None:
    host_config = HostConfig(name="host", ipv4_config=IPv4Config(address="11.211.3.32"))
    commands = list(special_agent_kube(params, host_config))
    assert len(commands) == 1
    arguments = commands[0].command_arguments
    for argument, argument_after in zip(arguments[:-1], arguments[1:]):
        if argument == "--api-server-proxy":
            assert expected_proxy_arg == argument_after
            return
    assert False, "--api-server-proxy is missing"
