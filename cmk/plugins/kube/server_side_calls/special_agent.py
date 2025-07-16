#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence
from typing import Literal

import pydantic

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)


class Timeout(pydantic.BaseModel, frozen=True):
    connect: int | None = None
    read: int | None = None


class UsageEndpoint(pydantic.BaseModel, frozen=True):
    endpoint_v2: str
    verify_cert: bool
    proxy: URLProxy | NoProxy | EnvProxy | None = EnvProxy()
    timeout: Timeout | None = None


class KubernetesAPIServer(pydantic.BaseModel, frozen=True):
    endpoint_v2: str
    verify_cert: bool
    proxy: URLProxy | NoProxy | EnvProxy | None = EnvProxy()
    timeout: Timeout | None = None


class Params(pydantic.BaseModel, frozen=True):
    cluster_name: str
    token: Secret
    monitored_objects: Sequence[str]
    namespaces: (
        tuple[Literal["namespace_include_patterns"], list[str]]
        | tuple[Literal["namespace_exclude_patterns"], list[str]]
        | None
    ) = None
    cluster_resource_aggregation: (
        tuple[Literal["cluster_aggregation_include_all_nodes"], None]
        | tuple[Literal["cluster_aggregation_exclude_node_roles"], list[str]]
        | None
    ) = None
    import_annotations: (
        tuple[Literal["include_matching_annotations_as_host_labels"], str]
        | tuple[Literal["include_annotations_as_host_labels"], None]
        | None
    ) = None
    kubernetes_api_server: KubernetesAPIServer
    usage_endpoint: tuple[Literal["prometheus", "cluster_collector"], UsageEndpoint] | None = None


def _timeouts(timeouts: Timeout, arg_prefix: Literal["k8s-api", "usage"]) -> Sequence[str]:
    args = []
    if (connect := timeouts.connect) is not None:
        args.append(f"--{arg_prefix}-connect-timeout")
        args.append(str(connect))
    if (read := timeouts.read) is not None:
        args.append(f"--{arg_prefix}-read-timeout")
        args.append(str(read))
    return args


def _usage_endpoint(
    params: UsageEndpoint, prefix: Literal["prometheus", "cluster_collector"]
) -> list[str]:
    args = ["--prometheus-endpoint" if prefix == "prometheus" else "--cluster-collector-endpoint"]
    args.append(params.endpoint_v2)
    match params.proxy:
        case URLProxy(url=url):
            args += ["--usage-proxy", url]
        case EnvProxy():
            args += ["--usage-proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--usage-proxy", "NO_PROXY"]
    if params.verify_cert:
        args.append("--usage-verify-cert")
    if timeouts := params.timeout:
        args.extend(_timeouts(timeouts, "usage"))
    return args


def command_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = ["--cluster", params.cluster_name]
    args.extend(["--kubernetes-cluster-hostname", host_config.name])
    args.extend(["--token", params.token.unsafe()])

    args.append("--monitored-objects")
    args.extend(params.monitored_objects)

    match params.namespaces:
        case ("namespace_include_patterns", namespace_patterns):
            args.append("--namespace-include-patterns")
            args.extend(namespace_patterns)
        case ("namespace_exclude_patterns", namespace_patterns):
            args.append("--namespace-exclude-patterns")
            args.extend(namespace_patterns)

    match params.cluster_resource_aggregation:
        case None:
            args.extend(["--cluster-aggregation-exclude-node-roles", "control-plane", "infra"])
        case ("cluster_aggregation_include_all_nodes", None):
            args.append("--cluster-aggregation-include-all-nodes")
        case ("cluster_aggregation_exclude_node_roles", list(excluded_roles)):
            args.append("--cluster-aggregation-exclude-node-roles")
            args.extend(excluded_roles)

    match params.import_annotations:
        case ("include_annotations_as_host_labels", None):
            args.append("--include-annotations-as-host-labels")
        case ("include_matching_annotations_as_host_labels", str(labels_param)):
            args.append("--include-matching-annotations-as-host-labels")
            args.append(labels_param)

    args.extend(["--api-server-endpoint", params.kubernetes_api_server.endpoint_v2])
    match params.kubernetes_api_server.proxy:
        case URLProxy(url=url):
            args += ["--api-server-proxy", url]
        case EnvProxy():
            args += ["--api-server-proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--api-server-proxy", "NO_PROXY"]
    if params.kubernetes_api_server.verify_cert:
        args.append("--verify-cert-api")
    if params.kubernetes_api_server.timeout is not None:
        args.extend(_timeouts(params.kubernetes_api_server.timeout, "k8s-api"))

    if params.usage_endpoint is not None:
        args.extend(_usage_endpoint(params.usage_endpoint[1], params.usage_endpoint[0]))
    yield SpecialAgentCommand(command_arguments=args)


special_agent_kube = SpecialAgentConfig(
    name="kube",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
