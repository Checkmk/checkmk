#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from typing import Any, Literal, Mapping, Optional, Sequence, Union

from cmk.base.check_api import get_http_proxy, passwordstore_get_cmdline
from cmk.base.config import special_agent_info


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
    params: Mapping[str, object], prefix: Literal["prometheus", "cluster-collector"]
) -> list[str]:
    args = [
        f"--{prefix}-endpoint",
        str(params["endpoint"]),
        "--usage-proxy",
        get_http_proxy(params.get("proxy", ("environment", "environment"))).serialize(),
    ]
    if params.get("verify-cert"):
        args.append("--usage-verify-cert")
    if timeouts := params.get("timeout"):
        args.extend(_timeouts(timeouts, "usage"))  # type: ignore[arg-type]
    return args


def agent_kube_arguments(  # pylint: disable=too-many-branches
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> Sequence[Union[str, tuple[str, str, str]]]:
    args = ["--cluster", params["cluster-name"]]
    args.extend(["--kubernetes-cluster-hostname", hostname])
    args.extend(["--token", passwordstore_get_cmdline("%s", params["token"])])

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
    args.extend(["--api-server-endpoint", api_params["endpoint"]])
    if api_params.get("verify-cert"):
        args.append("--verify-cert-api")
    args.extend(
        [
            "--api-server-proxy",
            get_http_proxy(api_params.get("proxy", ("environment", "environment"))).serialize(),
        ]
    )
    if api_timeouts := api_params.get("timeout"):
        args.extend(_timeouts(api_timeouts, "k8s-api"))

    if (endpoint_params := params.get("usage_endpoint")) is not None:
        return args + _usage_endpoint(endpoint_params[1], endpoint_params[0])

    return args


special_agent_info["kube"] = agent_kube_arguments
