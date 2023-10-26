#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel

from cmk.config_generation.v1 import (
    get_http_proxy,
    get_secret_from_params,
    HostConfig,
    HTTPProxy,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class ProxyParams(BaseModel):
    proxy: tuple[Literal["global", "environment", "url", "no_proxy"], str | None] = (
        "environment",
        "environment",
    )


def _timeouts(timeouts: Mapping[str, int], arg_prefix: str) -> Sequence[str]:
    args = []
    if (connect := timeouts.get("connect")) is not None:
        args.append(f"--{arg_prefix}-connect-timeout")
        args.append(str(connect))
    if (read := timeouts.get("read")) is not None:
        args.append(f"--{arg_prefix}-read-timeout")
        args.append(str(read))
    return args


def _usage_endpoint(
    params: Mapping[str, object],
    prefix: Literal["prometheus", "cluster-collector"],
    http_proxies: Mapping[str, HTTPProxy],
) -> list[str]:
    proxy_params = ProxyParams.model_validate(params)
    args = [
        f"--{prefix}-endpoint",
        str(params["endpoint_v2"]),
        "--usage-proxy",
        get_http_proxy(*proxy_params.proxy, http_proxies),
    ]
    if params.get("verify-cert"):
        args.append("--usage-verify-cert")
    if timeouts := params.get("timeout"):
        args.extend(_timeouts(timeouts, "usage"))  # type: ignore[arg-type]
    return args


def generate_kube_command(  # pylint: disable=too-many-branches
    params: Mapping[str, Any], host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    args = ["--cluster", params["cluster-name"]]
    args.extend(["--kubernetes-cluster-hostname", host_config.name])
    args.extend(["--token", get_secret_from_params(*params["token"])])

    args.append("--monitored-objects")
    args.extend(params["monitored-objects"])

    if "namespaces" in params:
        namespace_filter_option, filter_patterns = params["namespaces"]
        for namespace_pattern in filter_patterns:
            args.append(f"--{namespace_filter_option}")
            args.append(namespace_pattern)

    if "cluster-resource-aggregation" in params:
        if params["cluster-resource-aggregation"] == "cluster-aggregation-include-all-nodes":
            args.append("--cluster-aggregation-include-all-nodes")
        else:
            args.append("--cluster-aggregation-exclude-node-roles")
            args.extend(params["cluster-resource-aggregation"][1])
    else:
        args.extend(["--cluster-aggregation-exclude-node-roles", "control-plane", "infra"])

    if (host_labels_param := params.get("import-annotations")) is not None:
        if host_labels_param == "include-annotations-as-host-labels":
            args.append("--include-annotations-as-host-labels")
        else:
            args.append("--include-matching-annotations-as-host-labels")
            args.append(host_labels_param[1])

    api_params = params["kubernetes-api-server"]
    args.extend(["--api-server-endpoint", api_params["endpoint_v2"]])
    if api_params.get("verify-cert"):
        args.append("--verify-cert-api")
    proxy_params = ProxyParams.model_validate(api_params)
    args.extend(
        [
            "--api-server-proxy",
            get_http_proxy(*proxy_params.proxy, http_proxies),
        ]
    )
    if api_timeouts := api_params.get("timeout"):
        args.extend(_timeouts(api_timeouts, "k8s-api"))

    if (endpoint_params := params.get("usage_endpoint")) is not None:
        args += _usage_endpoint(endpoint_params[1], endpoint_params[0], http_proxies)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_kube = SpecialAgentConfig(
    name="kube", parameter_parser=noop_parser, commands_function=generate_kube_command
)
